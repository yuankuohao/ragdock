SHELL := /bin/bash
-include .env
export

.PHONY: help init fetch up down restart logs ps health smoke model model-chat test offline-save offline-load clean

help: ## 列出所有命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

init: ## 生成 .env
	@test -f .env || (cp .env.example .env && echo "已生成 .env，请先填写 API key 与企微参数")

fetch: ## 下载 RAGFlow 官方 compose 到 upstream/
	./scripts/fetch-upstream.sh

up: ## 启动全部服务
	./scripts/up.sh

down: ## 停止服务（保留数据）
	-@docker compose -f upstream/docker-compose.yml -p ragflow down 2>/dev/null
	docker compose down

restart: ## 只重启网关与企微适配
	docker compose up -d --force-recreate gateway wecom

logs: ## 跟踪日志
	docker compose logs -f --tail=100

ps: ## 查看容器
	@docker compose -f upstream/docker-compose.yml -p ragflow ps 2>/dev/null
	@docker compose ps

health: ## 探活三个服务
	./scripts/healthcheck.sh

smoke: ## 真实调用一次（网关 + 向量 + RAGFlow）
	./scripts/smoke-test.sh

model: ## 切换模型预设，例：make model PROFILE=qwen
	@test -n "$(PROFILE)" || (echo "用法：make model PROFILE=deepseek|qwen|kimi|glm|openai|ollama" && exit 1)
	python3 scripts/modelctl.py apply $(PROFILE)
	docker compose up -d --force-recreate gateway

model-chat: ## 只换聊天模型，例：make model-chat LLM_MODEL=qwen-max LLM_BASE_URL=... LLM_API_KEY=...
	python3 scripts/modelctl.py set LLM_MODEL=$(LLM_MODEL) LLM_BASE_URL=$(LLM_BASE_URL) LLM_API_KEY=$(LLM_API_KEY)
	python3 scripts/modelctl.py render
	docker compose up -d --force-recreate gateway

test: ## 不依赖 Docker 的配置校验
	./tests/run.sh

offline-save: ## 导出全部镜像（约 8-12 GB）
	./scripts/offline-save.sh

offline-load: ## 在目标机器导入镜像
	./scripts/offline-load.sh

clean: ## 删除本套件容器（不动数据卷）
	docker compose down --rmi local --remove-orphans
