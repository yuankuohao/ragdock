# upstream/

RAGFlow 官方 compose 的运行位置，由 `make fetch` 写入，**不纳入版本管理**。

为什么不在本仓库里复制一份：官方 compose 会随版本改动（新增服务、换镜像、调依赖），复制一份等于给自己埋一个会过期的分支。这里只存版本号，升级时删掉目录重跑 `make fetch`。

```bash
rm -rf upstream && RAGFLOW_VERSION=v1.0.0 make fetch
```

来源：<https://github.com/infiniflow/ragflow/tree/main/docker>
