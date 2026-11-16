# ragdock Agent 入口

先读[全局约束](CLAUDE.md)和[文档导航](docs/README.md)，然后只补本次影响范围需要的材料；已读且未变化的规则不重复全量读取。

## 事实源

| 问题 | 看哪里 |
|---|---|
| 项目是什么、为什么这样拆 | `README.md` |
| 改动的硬约束 | `CLAUDE.md` |
| 部署、模型、企微、离线怎么操作 | `docs/kb/`（先查索引） |
| 当前生效的模型与端口 | `.env` + `profiles/` |
| 生成的网关配置 | `gateway/generated.yaml`（由脚本生成，勿手改） |

## 交付前

跑 `make test`；涉及运行态再跑 `make health`、`make smoke`。结果按实际输出记录，未跑通的不写成通过。镜像构建、真实企微回调等无法在本机验证时，明确说明未验证。

## 边界

- 不提交 `.env`、密钥、客户文档或知识库导出。
- 不手改 `gateway/generated.yaml`、`upstream/`。
- KB 写入、推送远端、改动客户环境前先取得明确授权。
