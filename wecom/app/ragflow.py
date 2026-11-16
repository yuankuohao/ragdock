from __future__ import annotations

import logging
import time
from collections import OrderedDict

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class History:
    """按用户保存最近若干轮对话，进程内存储。多副本部署需换 Redis。"""

    def __init__(self, turns: int) -> None:
        self.turns = turns
        self._data: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._touched: dict[str, float] = {}

    def get(self, user_id: str) -> list[dict[str, str]]:
        return list(self._data.get(user_id, []))

    def append(self, user_id: str, role: str, content: str) -> None:
        if self.turns <= 0:
            return
        items = self._data.setdefault(user_id, [])
        items.append({"role": role, "content": content})
        del items[:-2 * self.turns]
        self._touched[user_id] = time.time()
        self._prune()

    def _prune(self) -> None:
        if len(self._touched) < 500:
            return
        cutoff = time.time() - 6 * 3600
        for user_id, ts in list(self._touched.items()):
            if ts < cutoff:
                self._touched.pop(user_id, None)
                self._data.pop(user_id, None)


class RagFlowClient:
    """调用 RAGFlow 的 OpenAI 兼容接口，使用聊天助手自身的检索与提示词配置。"""

    def __init__(self) -> None:
        self.history = History(settings.history_turns)

    async def ask(self, question: str, user_id: str, chat_id: str) -> str:
        if not chat_id:
            raise RuntimeError("未配置 RAGFLOW_CHAT_ID")
        messages = self.history.get(user_id) + [{"role": "user", "content": question}]
        url = f"{settings.ragflow_base}/api/v1/openai/{chat_id}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.ragflow_key}"}

        async with httpx.AsyncClient(timeout=settings.timeout) as client:
            response = await client.post(
                url, headers=headers, json={"messages": messages, "stream": False}
            )
        response.raise_for_status()
        payload = response.json()

        choices = payload.get("choices")
        if not choices:
            raise RuntimeError(f"RAGFlow 返回异常：code={payload.get('code')} {payload.get('message')}")

        answer = (choices[0].get("message") or {}).get("content", "").strip()
        self.history.append(user_id, "user", question)
        self.history.append(user_id, "assistant", answer)
        return answer
