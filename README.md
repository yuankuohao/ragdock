# ragdock

把 RAG 知识库停靠到任何环境：一条命令起一套可私有化部署的问答系统，模型在 6 个预设间随时切换，企业微信直接接入。

Self-hosted RAG in a box: one command brings up a private knowledge-base assistant, switches between six model presets at runtime, and plugs straight into WeCom.

[中文](#中文) · [English](#english)

---

## 中文

不是 SaaS，是给客户装在他自己机器上的东西。数据不出厂、不依赖任何境外服务、不需要备案主体（备案是客户的事）。

```
                 ┌──────────────────────────────────────────────┐
   企业微信 ───▶  │  wecom-adapter (:8088)                        │
                 │  验签 → 解密 → 取历史 → 调 RAGFlow → 主动回复  │
                 └───────────────┬──────────────────────────────┘
                                 │ OpenAI 兼容
                 ┌───────────────▼──────────────────────────────┐
   浏览器   ───▶  │  RAGFlow (:80 / API :9380)                    │
                 │  deepdoc 解析（OCR/版面/表格）→ 切块 → 检索    │
                 └───────────────┬──────────────────────────────┘
                                 │ base_url 指向网关
                 ┌───────────────▼──────────────────────────────┐
                 │  model-gateway / LiteLLM (:4000)              │
                 │  chat-default / embed-default / rerank-default│
                 └───┬────────┬────────┬────────┬───────────────┘
                 DeepSeek   Qwen    Kimi     GLM   Ollama(本地)
```

### 为什么这样拆

| 决定 | 原因 |
|---|---|
| 底座用 RAGFlow，不用 Dify | deepdoc 自带 OCR 与版面分析，扫描版手册能进；Apache-2.0 无附加限制，私有化交付不触发任何义务 |
| 模型走 LiteLLM 网关 | RAGFlow 只认一个 `base_url`；换模型改网关配置即可，**不用动 RAGFlow 的知识库与助手** |
| 企微单独做一层 | RAGFlow 没有企微通道；这层是交付里唯一不可替代的工程量 |
| 不用 `include` 合并官方 compose | 官方 compose 的镜像、网络、卷会随版本变；分开启动互不干扰，升级只换一个 tag |

### 快速开始

```bash
cp .env.example .env
vim .env                 # 填 LLM_API_KEY / EMBED_API_KEY / RAGFLOW_API_KEY / 企微四项

make fetch               # 拉取 RAGFlow 官方 compose（或按提示手动下载）
make up                  # 起 RAGFlow + 网关 + 企微适配
make health              # 三个服务探活
make smoke               # 打一次真实问答，验证链路
```

首次使用还要在 RAGFlow 网页（`http://<host>`）里做两件事，详见 [002 模型切换](docs/kb/002_模型切换.md)：

1. 模型供应商 → 新增 OpenAI-API-Compatible，Base URL 填 `http://<host>:4000/v1`，API Key 填 `.env` 里的 `LITELLM_MASTER_KEY`。
2. 建知识库 → 上传文档 → 建聊天助手 → 把助手 ID 填进 `.env` 的 `RAGFLOW_CHAT_ID`。

### 切换模型

```bash
make model PROFILE=qwen        # deepseek | qwen | kimi | glm | openai | ollama
make model-chat  LLM_MODEL=qwen-max LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 LLM_API_KEY=...
```

改完只重启网关（约 2 秒），RAGFlow 里的知识库、助手、会话全部不受影响。原理见 [002 模型切换](docs/kb/002_模型切换.md)。

### 目录

```
docker-compose.yml        网关 + 企微适配
upstream/                 RAGFlow 官方 compose（运行时拉取，不入库）
profiles/                 6 套模型预设
gateway/generated.yaml    由 profiles + .env 渲染，勿手改
wecom/                    企微回调与回复
scripts/                  up/down/health/smoke/offline/modelctl
docs/kb/                  部署、模型、企微、离线交付
tests/                    不依赖 Docker 的配置校验
CLAUDE.md                 全局约束；AGENTS.md 为协作入口
```

### 交付前须知

- **不要改 RAGFlow 的 LOGO 或用它做多租户**：Apache-2.0 允许商用与私有化交付，但 Dify/FastGPT 那类「去标 + 多租户」限制不适用于 RAGFlow；本套件自身也不含任何去标逻辑。
- **离线交付**用 `make offline-save` / `make offline-load`，镜像总量约 8–12 GB，介质用移动硬盘。
- 企微主动回复需要把服务器出口 IP 加进企微后台的**可信 IP**，否则 `message/send` 会报 60020。

### 文档

- 文档导航：[docs/README.md](docs/README.md)
- 知识库索引：[docs/kb/README.md](docs/kb/README.md)
- 全局约束：[CLAUDE.md](CLAUDE.md)

### License

本仓库代码 MIT。RAGFlow 由其自身 Apache-2.0 授权，LiteLLM 为 MIT，均以独立容器运行、未修改源码。

---

## English

This is not a SaaS. It is something you install on the customer's own machine: no data leaves the plant, no dependency on overseas services, no ICP filing required for the deployment itself.

The architecture diagram is the one above. In short: RAGFlow does parsing (OCR, layout, tables) and retrieval; LiteLLM sits in front of it as the only `base_url`, so switching providers never touches your knowledge bases or assistants; a small adapter bridges WeCom callbacks, which RAGFlow does not support.

### Why this split

| Decision | Reason |
|---|---|
| RAGFlow as the base, not Dify | deepdoc ships OCR and layout analysis, so scanned manuals are indexable. Apache-2.0 with no extra clauses, so private delivery triggers no obligations. |
| LiteLLM as model gateway | RAGFlow accepts a single `base_url`. Switching models is a gateway config change; knowledge bases and assistants stay untouched. |
| WeCom as a separate layer | RAGFlow has no WeCom channel. This adapter is the part of the delivery that cannot be bought off the shelf. |
| No `include` of the upstream compose | Upstream images, networks and volumes change between releases. Separate stacks do not interfere, and upgrades are a tag change. |

### Quick start

```bash
cp .env.example .env
vim .env                 # set LLM_API_KEY / EMBED_API_KEY / RAGFLOW_API_KEY / WeCom values

make fetch               # download the upstream RAGFlow compose file
make up                  # start RAGFlow + gateway + WeCom adapter
make health              # probe all three services
make smoke               # one real question end to end
```

Then, in the RAGFlow UI (`http://<host>`), see [002 model switching](docs/kb/002_模型切换.md):

1. Add an OpenAI-API-Compatible provider. Base URL `http://<host>:4000/v1`, API key = `LITELLM_MASTER_KEY` from `.env`.
2. Create a dataset, upload documents, create a chat assistant, and put its ID in `RAGFLOW_CHAT_ID`.

### Switching models

```bash
make model PROFILE=qwen        # deepseek | qwen | kimi | glm | openai | ollama
make model-chat  LLM_MODEL=qwen-max LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 LLM_API_KEY=...
```

Only the gateway restarts (about two seconds). Datasets, assistants and sessions are unaffected. Details: [002 model switching](docs/kb/002_模型切换.md).

### Layout

```
docker-compose.yml        gateway + WeCom adapter
upstream/                 upstream RAGFlow compose, fetched at runtime, not committed
profiles/                 six model presets
gateway/generated.yaml    rendered from profiles + .env, do not edit
wecom/                    callback verification, decryption, replies
scripts/                  up/down/health/smoke/offline/modelctl
docs/kb/                  deployment, models, WeCom, offline delivery
tests/                    config checks that need no Docker
CLAUDE.md                 global constraints; AGENTS.md is the agent entry
```

### Before delivery

- **Do not remove RAGFlow branding or run it multi-tenant.** Apache-2.0 permits commercial and private use; the "no logo removal / no multi-tenant" clauses found in Dify/FastGPT do not apply here, and this kit contains no de-branding logic.
- **Offline delivery**: `make offline-save` / `make offline-load`. Images total roughly 8–12 GB, ship them on a portable drive.
- WeCom proactive replies require the server's egress IP in the WeCom console's trusted IP list, otherwise `message/send` fails with 60020.

### Docs

- Navigation: [docs/README.md](docs/README.md)
- Knowledge base index: [docs/kb/README.md](docs/kb/README.md)
- Global constraints: [CLAUDE.md](CLAUDE.md)

### License

Code in this repository is MIT. RAGFlow is Apache-2.0, LiteLLM is MIT, both run as unmodified containers.
