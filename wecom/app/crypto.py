"""企业微信回调加解密（WXBizMsgCrypt 的 Python 实现）。

签名 = sha1(sort(token, timestamp, nonce, encrypt) 拼接)
密文 = AES-256-CBC，key = base64(aes_key + "=")，iv = key[:16]
明文 = random(16) + msg_len(4, big-endian) + msg + receive_id，PKCS#7 补齐到 32 字节
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import struct

from Crypto.Cipher import AES

BLOCK = 32


class WeComCryptoError(ValueError):
    pass


class WeComCrypto:
    def __init__(self, token: str, aes_key: str, receive_id: str) -> None:
        self.token = token
        self.receive_id = receive_id
        key = base64.b64decode(aes_key + "=")
        if len(key) != 32:
            raise WeComCryptoError("EncodingAESKey 解码后必须是 32 字节")
        self.key = key

    def signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        items = sorted([self.token, timestamp, nonce, encrypt])
        return hashlib.sha1("".join(items).encode("utf-8")).hexdigest()

    def verify(self, msg_signature: str, timestamp: str, nonce: str, encrypt: str) -> None:
        if not hmac.compare_digest(self.signature(timestamp, nonce, encrypt), msg_signature):
            raise WeComCryptoError("签名校验失败")

    def decrypt(self, encrypt_b64: str) -> str:
        try:
            raw = base64.b64decode(encrypt_b64)
        except Exception as exc:  # noqa: BLE001
            raise WeComCryptoError("密文不是合法 base64") from exc
        if not raw or len(raw) % 16:
            raise WeComCryptoError("密文长度非法")

        plain = AES.new(self.key, AES.MODE_CBC, self.key[:16]).decrypt(raw)
        pad = plain[-1]
        if not 1 <= pad <= BLOCK or plain[-pad:] != bytes([pad]) * pad:
            raise WeComCryptoError("填充非法")
        plain = plain[:-pad]

        if len(plain) < 20:
            raise WeComCryptoError("明文过短")
        msg_len = struct.unpack(">I", plain[16:20])[0]
        if 20 + msg_len > len(plain):
            raise WeComCryptoError("消息长度非法")
        msg = plain[20:20 + msg_len].decode("utf-8")
        receive_id = plain[20 + msg_len:].decode("utf-8")
        if self.receive_id and receive_id != self.receive_id:
            raise WeComCryptoError("receive_id 不匹配")
        return msg
