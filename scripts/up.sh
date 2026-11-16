#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "[up] 缺少 .env，先执行 make init" >&2
  exit 1
fi

python3 scripts/modelctl.py render

if [ ! -f upstream/docker-compose.yml ]; then
  ./scripts/fetch-upstream.sh
fi

echo "[up] 启动 RAGFlow（官方 compose）"
docker compose -p ragflow -f upstream/docker-compose.yml up -d

echo "[up] 启动网关与企微适配"
docker compose up -d --build

./scripts/healthcheck.sh --wait
