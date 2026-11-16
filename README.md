# ragdock

把 RAG 知识库「停靠」到任何环境：一条命令起一套可私有化部署的问答系统，模型在 6 个预设之间随时切换，企业微信直接接入。

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

## 为什么这样拆

| 决定 | 原因 |
|---|---|
| 底座用 RAGFlow，不用 Dify | deepdoc 自带 OCR 与版面分析，扫描版手册能进；Apache-2.0 无附加限制，私有化交付不触发任何义务 |
| 模型走 LiteLLM 网关 | RAGFlow 只认一个 `base_url`；换模型改网关配置即可，**不用动 RAGFlow 的知识库与助手** |
| 企微单独做一层 | RAGFlow 没有企微通道；这层是交付里唯一不可替代的工程量 |
| 不用 `include` 合并官方 compose | 官方 compose 的镜像、网络、卷会随版本变；分开启动互不干扰，升级只换一个 tag |

## 快速开始

```bash
cp .env.example .env
vim .env                 # 填 LLM_API_KEY / EMBED_API_KEY / RAGFLOW_API_KEY / 企微四项

make fetch               # 拉取 RAGFlow 官方 compose（或按提示手动下载）
make up                  # 起 RAGFlow + 网关 + 企微适配
make health              # 三个服务探活
make smoke               # 打一次真实问答，验证链路
```

首次使用还要在 RAGFlow 网页（`http://<host>`）里做两件事，详见 `docs/02-模型切换.md`：

1. 模型供应商 → 新增 OpenAI-API-Compatible，Base URL 填 `http://<host>:4000/v1`，API Key 填 `.env` 里的 `LITELLM_MASTER_KEY`。
2. 建知识库 → 上传文档 → 建聊天助手 → 把助手 ID 填进 `.env` 的 `RAGFLOW_CHAT_ID`。

## 切换模型

```bash
make model PROFILE=qwen        # deepseek | qwen | kimi | glm | openai | ollama
make model-chat  LLM_MODEL=qwen-max LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 LLM_API_KEY=...
```

改完只重启网关（约 2 秒），RAGFlow 里的知识库、助手、会话全部不受影响。原理见 `docs/02-模型切换.md`。

## 目录

```
docker-compose.yml        网关 + 企微适配
upstream/                 RAGFlow 官方 compose（运行时拉取，不入库）
profiles/                 6 套模型预设
gateway/generated.yaml    由 profiles + .env 渲染，勿手改
wecom/                    企微回调与回复
scripts/                  up/down/health/smoke/offline/modelctl
docs/                     部署、模型、企微、离线交付
tests/                    不依赖 Docker 的配置校验
```

## 交付前须知

- **不要改 RAGFlow 的 LOGO 或用它做多租户**：Apache-2.0 允许商用与私有化交付，但 Dify/FastGPT 那类「去标 + 多租户」限制不适用于 RAGFlow；本套件自身也不含任何去标逻辑。
- **离线交付**用 `make offline-save` / `make offline-load`，镜像总量约 8–12 GB，介质用移动硬盘。
- 企微主动回复需要把服务器出口 IP 加进企微后台的**可信 IP**，否则 `message/send` 会报 60020。

## License

本仓库代码 MIT。RAGFlow 由其自身 Apache-2.0 授权，LiteLLM 为 MIT，均以独立容器运行、未修改源码。
