from __future__ import annotations

import logging
import time

import httpx

from .config import settings

logger = logging.getLogger(__name__)

API = "https://qyapi.weixin.qq.com/cgi-bin"


class WeComApi:
    """主动发消息与通讯录查询。需要把出口 IP 加入企微后台的可信 IP。"""

    def __init__(self) -> None:
        self._token = ""
        self._token_expire = 0.0
        self._dept_cache: dict[str, tuple[list[str], float]] = {}

    async def access_token(self) -> str:
        if self._token and time.time() < self._token_expire:
            return self._token
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{API}/gettoken",
                params={"corpid": settings.corp_id, "corpsecret": settings.secret},
            )
        payload = response.json()
        if payload.get("errcode") != 0:
            raise RuntimeError(f"获取 access_token 失败：{payload}")
        # 官方有效期 7200 秒，提前 5 分钟刷新
        self._token = payload["access_token"]
        self._token_expire = time.time() + int(payload.get("expires_in", 7200)) - 300
        return self._token

    async def send_text(self, user_id: str, content: str) -> None:
        token = await self.access_token()
        body = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": int(settings.agent_id),
            "text": {"content": content},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{API}/message/send", params={"access_token": token}, json=body
            )
        payload = response.json()
        if payload.get("errcode") != 0:
            raise RuntimeError(f"发送消息失败：{payload}")

    async def departments(self, user_id: str) -> list[str]:
        cached = self._dept_cache.get(user_id)
        if cached and time.time() < cached[1]:
            return cached[0]
        token = await self.access_token()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{API}/user/get", params={"access_token": token, "userid": user_id}
            )
        payload = response.json()
        if payload.get("errcode") != 0:
            logger.warning("读取部门失败 user=%s payload=%s", user_id, payload)
            return []
        depts = [str(item) for item in payload.get("department", [])]
        self._dept_cache[user_id] = (depts, time.time() + 600)
        return depts

    async def resolve_chat_id(self, user_id: str) -> str:
        """WECOM_ROUTES 为空时用默认助手；否则按部门匹配，未命中回落默认。"""
        if not settings.routes:
            return settings.chat_id
        for dept in await self.departments(user_id):
            if dept in settings.routes:
                return settings.routes[dept]
        return settings.chat_id
