#!/usr/bin/env python3
"""读取 .env / profiles 并渲染 LiteLLM 网关配置。

子命令：
  render [--env PATH] [--out PATH]     渲染 gateway/generated.yaml
  apply PROFILE                        应用 profiles/<PROFILE>.env
  set K=V [K=V ...]                    只改指定键
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "profiles"


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def update_env(path: Path, changes: dict[str, str]) -> None:
    """保留注释与顺序，只替换指定键；不存在的键追加到末尾。"""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = dict(changes)
    out: list[str] = []
    for line in lines:
        match = re.match(r"^(\s*)([A-Z0-9_]+)\s*=", line)
        if match and match.group(2) in pending:
            key = match.group(2)
            out.append(f"{key}={pending.pop(key)}")
        else:
            out.append(line)
    if pending:
        out.append("")
        out.append("# 由 scripts/modelctl.py 写入")
        for key, value in pending.items():
            out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def require(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        sys.exit(f"[modelctl] .env 缺少 {key}，先 make init 并填写")
    return value


def render(env_path: Path, out_path: Path) -> None:
    env = parse_env(env_path)
    chat_base = require(env, "LLM_BASE_URL").rstrip("/")
    chat_model = require(env, "LLM_MODEL")
    embed_base = require(env, "EMBED_BASE_URL").rstrip("/")
    embed_model = require(env, "EMBED_MODEL")
    master_key = env.get("LITELLM_MASTER_KEY", "sk-ragdoc-local")

    entries: list[str] = []

    def add(name: str, model: str, base: str, key_var: str) -> None:
        entries.append(
            f"  - model_name: {name}\n"
            f"    litellm_params:\n"
            f"      model: openai/{model}\n"
            f"      api_base: {base}\n"
            f"      api_key: os.environ/{key_var}"
        )

    add("chat-default", chat_model, chat_base, "LLM_API_KEY")
    if chat_model != "chat-default":
        add(chat_model, chat_model, chat_base, "LLM_API_KEY")
    add("embed-default", embed_model, embed_base, "EMBED_API_KEY")
    if embed_model != "embed-default":
        add(embed_model, embed_model, embed_base, "EMBED_API_KEY")

    content = (
        "# 本文件由 scripts/modelctl.py 生成，请勿手改。\n"
        "# 改模型：make model PROFILE=qwen 或 make model-chat LLM_MODEL=...\n"
        "\n"
        "model_list:\n" + "\n".join(entries) + "\n"
        "\n"
        "litellm_settings:\n"
        "  drop_params: true\n"
        "  num_retries: 2\n"
        "  request_timeout: 600\n"
        "\n"
        "general_settings:\n"
        f"  master_key: {master_key}\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    try:
        shown = out_path.relative_to(ROOT)
    except ValueError:
        shown = out_path
    print(f"[modelctl] 已渲染 {shown}")
    print(f"[modelctl]   chat  = {chat_model}")
    print(f"[modelctl]   embed = {embed_model}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ragdoc 模型配置工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_render = sub.add_parser("render", help="渲染网关配置")
    p_render.add_argument("--env", type=Path, default=ROOT / ".env")
    p_render.add_argument("--out", type=Path, default=ROOT / "gateway" / "generated.yaml")

    p_apply = sub.add_parser("apply", help="应用预设")
    p_apply.add_argument("profile")
    p_apply.add_argument("--env", type=Path, default=ROOT / ".env")

    p_set = sub.add_parser("set", help="写入键值")
    p_set.add_argument("pairs", nargs="+")
    p_set.add_argument("--env", type=Path, default=ROOT / ".env")

    args = parser.parse_args()

    if args.cmd == "render":
        render(args.env, args.out)
    elif args.cmd == "apply":
        if not args.env.exists():
            sys.exit("[modelctl] 缺少 .env，先执行 make init")
        profile = PROFILE_DIR / f"{args.profile}.env"
        if not profile.exists():
            available = ", ".join(sorted(p.stem for p in PROFILE_DIR.glob("*.env")))
            sys.exit(f"[modelctl] 没有预设 {args.profile}，可用：{available}")
        changes = parse_env(profile)
        update_env(args.env, changes)
        print(f"[modelctl] 已应用预设 {args.profile}")
        render(args.env, ROOT / "gateway" / "generated.yaml")
    else:
        changes = {}
        for pair in args.pairs:
            if "=" not in pair:
                sys.exit(f"[modelctl] 参数格式应为 KEY=VALUE：{pair}")
            key, _, value = pair.partition("=")
            changes[key.strip()] = value.strip()
        update_env(args.env, changes)
        print(f"[modelctl] 已更新 {', '.join(changes)}")


if __name__ == "__main__":
    main()
