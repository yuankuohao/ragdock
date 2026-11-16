#!/usr/bin/env bash
# 在目标机器导入离线镜像：./scripts/offline-load.sh offline/ragdoc-images-YYYYMMDD.tar.gz
set -euo pipefail
cd "$(dirname "$0")/.."

FILE="${1:-}"
if [ -z "$FILE" ]; then
  FILE=$(ls -t offline/*.tar.gz 2>/dev/null | head -1 || true)
fi
[ -n "$FILE" ] && [ -f "$FILE" ] || { echo "用法：$0 <镜像归档.tar.gz>" >&2; exit 1; }

echo "[offline] 导入 $FILE"
gunzip -c "$FILE" | docker load
echo "[offline] 完成。确认 upstream/ 与 .env 已就位后执行 make up"
