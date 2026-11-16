#!/usr/bin/env bash
# 不依赖 Docker 的校验：脚本语法、Python 语法、配置渲染、预设完整性。
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0
note() { printf '%s\n' "$*"; }
ok() { printf '  [ok]   %s\n' "$*"; }
bad() { printf '  [fail] %s\n' "$*"; fail=1; }

note "[test] 1/7 Shell 语法"
for f in scripts/*.sh tests/*.sh; do
  if bash -n "$f"; then ok "$f"; else bad "$f"; fi
done

note "[test] 2/7 Python 语法"
if python3 -m py_compile scripts/modelctl.py wecom/app/*.py; then ok "py_compile"; else bad "py_compile"; fi

note "[test] 3/7 渲染网关配置"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp .env.example "$tmp/.env"
if python3 scripts/modelctl.py render --env "$tmp/.env" --out "$tmp/generated.yaml" >/dev/null; then
  ok "render"
else
  bad "render"
fi
for key in "model_name: chat-default" "model_name: embed-default" "master_key:"; do
  if grep -q "$key" "$tmp/generated.yaml" 2>/dev/null; then ok "包含 $key"; else bad "缺少 $key"; fi
done

note "[test] 4/7 应用预设"
if python3 scripts/modelctl.py apply qwen --env "$tmp/.env" >/dev/null; then
  if grep -q "^LLM_PROFILE=qwen$" "$tmp/.env" && grep -q "^LLM_MODEL=qwen-plus$" "$tmp/.env"; then
    ok "预设 qwen 生效"
  else
    bad "预设未写入 .env"
  fi
else
  bad "apply"
fi

note "[test] 5/7 预设文件完整性"
for f in profiles/*.env; do
  for key in LLM_BASE_URL LLM_MODEL EMBED_BASE_URL EMBED_MODEL; do
    if grep -q "^${key}=" "$f"; then :; else bad "$f 缺少 $key"; fi
  done
done
[ "$fail" -eq 0 ] && ok "全部预设含 4 个必填键"

note "[test] 6/7 企微解密自测"
if python3 -c "import Crypto" >/dev/null 2>&1; then
  if python3 tests/test_crypto.py; then :; else bad "test_crypto"; fi
else
  note "  [skip] 未安装 pycryptodome；可在容器内执行："
  note "         docker run --rm -v \$PWD:/w -w /w python:3.11-slim sh -c 'pip -q install pycryptodome && python tests/test_crypto.py'"
fi

note "[test] 7/7 适配层接口"
if python3 -c "import fastapi, httpx, defusedxml" >/dev/null 2>&1; then
  if python3 tests/test_app.py; then :; else bad "test_app"; fi
else
  note "  [skip] 未安装 fastapi/httpx/defusedxml"
  note "         pip3 install --user fastapi 'httpx<1' defusedxml"
fi

echo
[ "$fail" -eq 0 ] && echo "[test] 通过" || echo "[test] 有失败项"
exit "$fail"
