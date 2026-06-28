# KZ-030 基础架构升级：Alembic + 部署脚本

## 目标

让 Project Kizuna 后续数据库变更可追踪、可部署、可回滚，减少手工改表风险。

## 本次交付

- Alembic 初始化
- Baseline migration
- 生产部署脚本
- LF 换行规范
- 数据库迁移说明文档

## 验收清单

- `docker compose up -d --build` 成功。
- `docker compose exec -T backend alembic -c alembic.ini current` 可执行。
- `docker compose exec -T backend alembic -c alembic.ini stamp head` 可执行。
- 网站可正常登录。
