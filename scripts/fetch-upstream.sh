#!/usr/bin/env bash
# 下载 RAGFlow 官方 compose 到 upstream/。国内网络依次尝试镜像。
set -euo pipefail
cd "$(dirname "$0")/.."

: "${RAGFLOW_VERSION:=v1.0.0}"
: "${RAGFLOW_REPO:=infiniflow/ragflow}"
DEST=upstream
mkdir -p "$DEST"

if [ -f "$DEST/docker-compose.yml" ] && [ -f "$DEST/.env" ]; then
  echo "[fetch] upstream/ 已存在，跳过。要升级请先删除该目录。"
  exit 0
fi

MIRRORS=(
  "https://raw.githubusercontent.com/${RAGFLOW_REPO}/${RAGFLOW_VERSION}/docker"
  "https://ghfast.top/https://raw.githubusercontent.com/${RAGFLOW_REPO}/${RAGFLOW_VERSION}/docker"
  "https://gh-proxy.com/https://raw.githubusercontent.com/${RAGFLOW_REPO}/${RAGFLOW_VERSION}/docker"
)

ok=0
for base in "${MIRRORS[@]}"; do
  echo "[fetch] 尝试 $base"
  if curl -fsSL --max-time 40 "$base/docker-compose.yml" -o "$DEST/docker-compose.yml" \
     && curl -fsSL --max-time 40 "$base/.env" -o "$DEST/.env"; then
    ok=1
    break
  fi
done

if [ "$ok" -ne 1 ]; then
  cat >&2 <<EOF
[fetch] 自动下载失败。请手动下载以下两个文件，放到 $(pwd)/upstream/ ：
  https://github.com/${RAGFLOW_REPO}/blob/${RAGFLOW_VERSION}/docker/docker-compose.yml
  https://github.com/${RAGFLOW_REPO}/blob/${RAGFLOW_VERSION}/docker/.env
然后重新执行 make up。
EOF
  exit 1
fi

# 把镜像 tag 钉在 RAGFLOW_VERSION 上，避免官方 .env 里的 nightly 漂移
sed -i.bak "s#^RAGFLOW_IMAGE=.*#RAGFLOW_IMAGE=infiniflow/ragflow:${RAGFLOW_VERSION}#" "$DEST/.env"
rm -f "$DEST/.env.bak"

echo "[fetch] 完成：$DEST/docker-compose.yml（tag ${RAGFLOW_VERSION}）"
