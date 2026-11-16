#!/usr/bin/env bash
# 探活：网关 / RAGFlow / 企微适配。--wait 会轮询最多 180 秒。
set -uo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] && set -a && . ./.env && set +a
GATEWAY_PORT="${GATEWAY_PORT:-4000}"
WECOM_PORT="${WECOM_PORT:-8088}"

WAIT=0
[ "${1:-}" = "--wait" ] && WAIT=1

check() {
  local name=$1 url=$2
  if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
    echo "  [ok]   $name"
    return 0
  fi
  echo "  [fail] $name  ($url)"
  return 1
}

run_all() {
  local failed=0
  check "model-gateway :${GATEWAY_PORT}" "http://127.0.0.1:${GATEWAY_PORT}/health/liveliness" || failed=1
  check "ragflow-api    :9380" "http://127.0.0.1:9380/api/v1/system/healthz" || failed=1
  check "wecom-adapter  :${WECOM_PORT}" "http://127.0.0.1:${WECOM_PORT}/healthz" || failed=1
  return $failed
}

if [ "$WAIT" -eq 0 ]; then
  run_all
  exit $?
fi

echo "[health] 等待服务就绪（最多 180 秒）"
for _ in $(seq 1 36); do
  if run_all >/dev/null 2>&1; then
    run_all
    echo "[health] 全部就绪"
    exit 0
  fi
  sleep 5
done

run_all
echo "[health] 超时，见 docker compose logs" >&2
exit 1
