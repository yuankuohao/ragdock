#!/usr/bin/env python3
"""企微回调解密的自测。不依赖网络与企业微信。"""
from __future__ import annotations

import base64
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "wecom"))

from Crypto.Cipher import AES  # noqa: E402

from app.crypto import WeComCrypto, WeComCryptoError  # noqa: E402


def encrypt(msg: str, key: bytes, receive_id: str) -> str:
    body = msg.encode()
    data = os.urandom(16) + struct.pack(">I", len(body)) + body + receive_id.encode()
    pad = 32 - len(data) % 32
    data += bytes([pad]) * pad
    return base64.b64encode(AES.new(key, AES.MODE_CBC, key[:16]).encrypt(data)).decode()


def main() -> int:
    raw_key = os.urandom(32)
    aes_key = base64.b64encode(raw_key).decode().rstrip("=")
    assert len(aes_key) == 43, len(aes_key)

    crypto = WeComCrypto("tok", aes_key, "ww123456")
    failures = 0

    for text in ["你好", "E07 主轴过载，先检查冷却液位。", "a" * 1000, "x" * 31]:
        cipher = encrypt(text, raw_key, "ww123456")
        got = crypto.decrypt(cipher)
        if got == text:
            print(f"  [ok]   roundtrip len={len(text)}")
        else:
            print(f"  [fail] roundtrip len={len(text)}")
            failures += 1

    cipher = encrypt("hi", raw_key, "other-corp")
    try:
        crypto.decrypt(cipher)
        print("  [fail] 错误 receive_id 未被拒绝")
        failures += 1
    except WeComCryptoError:
        print("  [ok]   错误 receive_id 被拒绝")

    sig = crypto.signature("1700000000", "abc", "ENCRYPTED")
    try:
        crypto.verify(sig, "1700000000", "abc", "ENCRYPTED")
        print("  [ok]   签名校验通过")
    except WeComCryptoError:
        print("  [fail] 正确签名被判失败")
        failures += 1

    try:
        crypto.verify("deadbeef", "1700000000", "abc", "ENCRYPTED")
        print("  [fail] 错误签名未被拒绝")
        failures += 1
    except WeComCryptoError:
        print("  [ok]   错误签名被拒绝")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
