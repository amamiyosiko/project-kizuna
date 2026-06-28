# Alembic 数据库迁移规范

Project Kizuna 从 v0.3.0 开始引入 Alembic，用于管理数据库结构变化。

## 当前策略

为了保护已有生产数据库，v0.3.0 采用 baseline 方式：

- 已有数据库：执行 `alembic stamp head`，只标记版本，不改表。
- 新增字段/表：后续版本通过 Alembic migration 管理。
- 过渡期仍保留 `Base.metadata.create_all()`，避免部署时缺表导致系统不可用。

## 生产服务器首次标记

```bash
cd /www/wwwroot/project-kizuna.mychisyou.com
docker compose exec -T backend alembic -c alembic.ini stamp head
```

## 后续版本升级

```bash
docker compose exec -T backend alembic -c alembic.ini upgrade head
```

## 生成新 migration

开发环境使用：

```bash
cd backend
alembic -c alembic.ini revision --autogenerate -m "add_xxx"
```

## 原则

- 不在生产环境手工改表。
- 所有结构变化必须进入 Alembic migration。
- 不随意删除字段；优先新增字段并兼容旧数据。
