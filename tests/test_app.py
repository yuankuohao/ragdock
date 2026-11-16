#!/usr/bin/env python3
"""适配层接口自测：健康检查、回调验签、解密返回。不联网。"""
from __future__ import annotations

import base64
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORP_ID = "wwtest0001"
TOKEN = "ragdoctoken"
RAW_KEY = bytes(range(32))
AES_KEY = base64.b64encode(RAW_KEY).decode().rstrip("=")

os.environ.update(
    {
        "WECOM_CORP_ID": CORP_ID,
        "WECOM_AGENT_ID": "1000002",
        "WECOM_SECRET": "secret",
        "WECOM_TOKEN": TOKEN,
        "WECOM_AES_KEY": AES_KEY,
        "RAGFLOW_API_KEY": "ragflow-key",
        "RAGFLOW_CHAT_ID": "chat-1",
        "RAGFLOW_BASE_URL": "http://127.0.0.1:1",
        "WECOM_ROUTES": '{"2": "chat-dept-2"}',
    }
)

sys.path.insert(0, str(ROOT / "wecom"))

from Crypto.Cipher import AES  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.crypto import WeComCrypto  # noqa: E402
from app.main import app  # noqa: E402


def encrypt(msg: str) -> str:
    body = msg.encode()
    data = os.urandom(16) + struct.pack(">I", len(body)) + body + CORP_ID.encode()
    pad = 32 - len(data) % 32
    data += bytes([pad]) * pad
    return base64.b64encode(AES.new(RAW_KEY, AES.MODE_CBC, RAW_KEY[:16]).encrypt(data)).decode()


def main() -> int:
    failures = 0
    crypto = WeComCrypto(TOKEN, AES_KEY, CORP_ID)

    with TestClient(app) as client:
        response = client.get("/healthz")
        body = response.json()
        if response.status_code == 200 and body["ok"] and body["routes"] == 1:
            print("  [ok]   /healthz 200")
        else:
            print(f"  [fail] /healthz {response.status_code} {body}")
            failures += 1

        echostr = encrypt("echo-back-123")
        params = {
            "msg_signature": crypto.signature("1700000000", "nonce", echostr),
            "timestamp": "1700000000",
            "nonce": "nonce",
            "echostr": echostr,
        }
        response = client.get("/wecom/callback", params=params)
        if response.status_code == 200 and response.text == "echo-back-123":
            print("  [ok]   回调验签并返回明文 echostr")
        else:
            print(f"  [fail] 回调 {response.status_code} {response.text!r}")
            failures += 1

        bad = dict(params, msg_signature="0" * 40)
        response = client.get("/wecom/callback", params=bad)
        if response.status_code == 403:
            print("  [ok]   错误签名返回 403")
        else:
            print(f"  [fail] 错误签名返回 {response.status_code}")
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
