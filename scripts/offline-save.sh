#!/usr/bin/env bash
# 导出全部镜像到 offline/，用于隔离网环境交付。
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p offline
STAMP=$(date +%Y%m%d)
OUT="offline/ragdock-images-${STAMP}.tar.gz"

echo "[offline] 构建本地镜像"
docker compose build

echo "[offline] 收集镜像清单"
{
  docker compose -p ragflow -f upstream/docker-compose.yml config --images 2>/dev/null || true
  docker compose config --images
} | sort -u > "offline/images-${STAMP}.txt"

echo "[offline] 共 $(wc -l < "offline/images-${STAMP}.txt") 个镜像，开始导出（耗时较久）"
# shellcheck disable=SC2046
docker save $(cat "offline/images-${STAMP}.txt") | gzip -1 > "$OUT"

cat > offline/MANIFEST.txt <<EOF
ragdock 离线包
导出时间: $(date '+%F %T')
RAGFlow:  ${RAGFLOW_VERSION:-unknown}
镜像清单: images-${STAMP}.txt
镜像归档: $(basename "$OUT")
目标机导入: gunzip -c $(basename "$OUT") | docker load
EOF

echo "[offline] 完成：$OUT ($(du -h "$OUT" | cut -f1))"
