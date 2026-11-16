from __future__ import annotations

import json
import os


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


class Settings:
    """启动时不校验，缺失项在 /healthz 里报出来，避免容器起不来。"""

    def __init__(self) -> None:
        self.corp_id = _env("WECOM_CORP_ID")
        self.agent_id = _env("WECOM_AGENT_ID")
        self.secret = _env("WECOM_SECRET")
        self.token = _env("WECOM_TOKEN")
        self.aes_key = _env("WECOM_AES_KEY")
        self.routes: dict[str, str] = json.loads(_env("WECOM_ROUTES", "{}") or "{}")

        self.ragflow_base = _env("RAGFLOW_BASE_URL", "http://host.docker.internal:9380").rstrip("/")
        self.ragflow_key = _env("RAGFLOW_API_KEY")
        self.chat_id = _env("RAGFLOW_CHAT_ID")
        self.timeout = float(_env("RAGFLOW_TIMEOUT", "90"))
        self.history_turns = int(_env("RAGFLOW_HISTORY_TURNS", "3"))

        self.max_chars = int(_env("WECOM_MAX_CHARS", "1500"))

    @property
    def wecom_ready(self) -> bool:
        return all([self.corp_id, self.agent_id, self.secret, self.token, self.aes_key])

    @property
    def ragflow_ready(self) -> bool:
        return bool(self.ragflow_key and self.chat_id)

    def missing(self) -> list[str]:
        checks = {
            "WECOM_CORP_ID": self.corp_id,
            "WECOM_AGENT_ID": self.agent_id,
            "WECOM_SECRET": self.secret,
            "WECOM_TOKEN": self.token,
            "WECOM_AES_KEY": self.aes_key,
            "RAGFLOW_API_KEY": self.ragflow_key,
            "RAGFLOW_CHAT_ID": self.chat_id,
        }
        return [k for k, v in checks.items() if not v]


settings = Settings()
