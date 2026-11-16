from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from .config import settings
from .crypto import WeComCrypto, WeComCryptoError
from .ragflow import RagFlowClient
from .wecom_api import WeComApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ragdoc.wecom")

MAX_BODY = 64 * 1024

state: dict[str, object] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    state["crypto"] = WeComCrypto(settings.token, settings.aes_key, settings.corp_id) if settings.wecom_ready else None
    state["ragflow"] = RagFlowClient()
    state["api"] = WeComApi()
    logger.info("启动完成，缺失配置：%s", settings.missing() or "无")
    yield
    state.clear()


app = FastAPI(title="ragdoc wecom adapter", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> JSONResponse:
    ready = settings.wecom_ready and settings.ragflow_ready
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "ok": ready,
            "wecom_ready": settings.wecom_ready,
            "ragflow_ready": settings.ragflow_ready,
            "missing": settings.missing(),
            "routes": len(settings.routes),
        },
    )


def _crypto() -> WeComCrypto:
    crypto = state.get("crypto")
    if not isinstance(crypto, WeComCrypto):
        raise HTTPException(status_code=503, detail="企微参数未配置完整")
    return crypto


@app.get("/wecom/callback", response_class=PlainTextResponse)
async def verify(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
) -> str:
    crypto = _crypto()
    try:
        crypto.verify(msg_signature, timestamp, nonce, echostr)
        return crypto.decrypt(echostr)
    except WeComCryptoError as exc:
        logger.warning("校验回调失败：%s", exc)
        raise HTTPException(status_code=403, detail="invalid signature") from exc


@app.post("/wecom/callback", response_class=PlainTextResponse)
async def receive(
    request: Request,
    background: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
) -> str:
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(status_code=413, detail="body too large")

    crypto = _crypto()
    try:
        outer = SafeET.fromstring(body)
        encrypted = outer.findtext("Encrypt") or ""
        crypto.verify(msg_signature, timestamp, nonce, encrypted)
        message = SafeET.fromstring(crypto.decrypt(encrypted))
    except (ET.ParseError, DefusedXmlException, WeComCryptoError) as exc:
        logger.warning("解密失败：%s", exc)
        raise HTTPException(status_code=403, detail="invalid payload") from exc

    msg_type = message.findtext("MsgType") or ""
    user_id = message.findtext("FromUserName") or ""
    if msg_type != "text" or not user_id:
        # 非文本消息直接忽略，让用户在企微里看到「未读」而不是错误提示
        return ""

    content = (message.findtext("Content") or "").strip()
    if not content:
        return ""

    # 企微要求 5 秒内响应，LLM 一定超时：先空响应，再异步主动发消息
    background.add_task(_answer, user_id, content)
    return ""


async def _answer(user_id: str, question: str) -> None:
    api: WeComApi = state["api"]  # type: ignore[assignment]
    ragflow: RagFlowClient = state["ragflow"]  # type: ignore[assignment]
    try:
        chat_id = await api.resolve_chat_id(user_id)
        answer = (await ragflow.ask(question, user_id, chat_id)).strip()
        if not answer:
            answer = "没有检索到相关内容，可以换个说法再问一次。"
        if len(answer) > settings.max_chars:
            answer = answer[: settings.max_chars] + "…"
        await api.send_text(user_id, answer)
    except Exception:  # noqa: BLE001
        logger.exception("处理失败 user=%s", user_id)
        try:
            await api.send_text(user_id, "服务暂时不可用，请稍后再试。")
        except Exception:  # noqa: BLE001
            logger.exception("兜底回复失败 user=%s", user_id)
