#!/usr/bin/env bash
# 三层冒烟：网关聊天 → 网关向量 → RAGFlow 端到端问答。
# 端到端一段需要 RAGFLOW_API_KEY 与 RAGFLOW_CHAT_ID，任一为空则跳过。
set -uo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] && set -a && . ./.env && set +a
GATEWAY_PORT="${GATEWAY_PORT:-4000}"
KEY="${LITELLM_MASTER_KEY:?缺少 LITELLM_MASTER_KEY}"

fail=0

echo "[smoke] 1/3 网关聊天"
python3 - "$GATEWAY_PORT" "$KEY" <<'PY' || fail=1
import json, sys, urllib.error, urllib.request
port, key = sys.argv[1], sys.argv[2]
req = urllib.request.Request(
    f"http://127.0.0.1:{port}/v1/chat/completions",
    data=json.dumps({"model": "chat-default",
                     "messages": [{"role": "user", "content": "只回复两个字：可以"}],
                     "max_tokens": 16}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
try:
    body = json.load(urllib.request.urlopen(req, timeout=60))
    print("  [ok]   " + body["choices"][0]["message"]["content"].strip()[:40])
except Exception as exc:  # noqa: BLE001
    print(f"  [fail] {exc}")
    sys.exit(1)
PY

echo "[smoke] 2/3 网关向量"
python3 - "$GATEWAY_PORT" "$KEY" <<'PY' || fail=1
import json, sys, urllib.request
port, key = sys.argv[1], sys.argv[2]
req = urllib.request.Request(
    f"http://127.0.0.1:{port}/v1/embeddings",
    data=json.dumps({"model": "embed-default", "input": "主轴过载报警"}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
try:
    body = json.load(urllib.request.urlopen(req, timeout=60))
    print(f"  [ok]   dim={len(body['data'][0]['embedding'])}")
except Exception as exc:  # noqa: BLE001
    print(f"  [fail] {exc}")
    sys.exit(1)
PY

if [ -z "${RAGFLOW_API_KEY:-}" ] || [ -z "${RAGFLOW_CHAT_ID:-}" ]; then
  echo "[smoke] 3/3 跳过：未配置 RAGFLOW_API_KEY / RAGFLOW_CHAT_ID"
else
  echo "[smoke] 3/3 RAGFlow 端到端"
  python3 - "${RAGFLOW_API_BASE:-http://127.0.0.1:9380}" "$RAGFLOW_API_KEY" "$RAGFLOW_CHAT_ID" <<'PY' || fail=1
import json, sys, urllib.request
base, key, chat_id = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
req = urllib.request.Request(
    f"{base}/api/v1/openai/{chat_id}/chat/completions",
    data=json.dumps({"messages": [{"role": "user", "content": "这个知识库里有什么？一句话回答"}],
                     "stream": False}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
try:
    body = json.load(urllib.request.urlopen(req, timeout=120))
    if "choices" in body:
        print("  [ok]   " + body["choices"][0]["message"]["content"].strip()[:60])
    else:
        print(f"  [fail] code={body.get('code')} {body.get('message')}")
        sys.exit(1)
except Exception as exc:  # noqa: BLE001
    print(f"  [fail] {exc}")
    sys.exit(1)
PY
fi

[ "$fail" -eq 0 ] && echo "[smoke] 通过" || { echo "[smoke] 有失败项" >&2; exit 1; }
