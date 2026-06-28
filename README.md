# Project Kizuna v0.1.0

Amazon JP AI 客服工作台 MVP。

## 本版本内容

- KZ-004 登录系统
- 默认管理员账号
- 登录后进入 `/workspace`
- 首次登录修改密码页
- 顶部导航与 Workspace 页面骨架
- Docker Compose：PostgreSQL / Redis / Backend / Frontend

## 启动

```bash
docker compose up
```

打开：

```text
http://localhost:3000
```

默认账号：

```text
admin / admin123456
```

## 后端健康检查

```text
http://localhost:8000/health
```

## v0.1.1 - KZ-005 店铺管理

新增店铺管理完整页面：新增、编辑、启用/停用、删除、搜索。

建议店铺编码使用 `JP01`、`JP02`、`JP03`，后续消息、订单和 S3 附件路径都会优先使用这个编码。

## Current Version

v0.1.2 - Customer Workspace

本版本新增客服四栏工作台，可手动录入 Amazon 买家消息，生成 AI 日语回复草稿，复制回复并标记完成。


## v0.1.3

KZ-007 AI 回复优化：新增可追溯分类、Intent、风险、置信度、三种日语回复语气。


## v0.1.4 KZ-008 S3 文件上传

新增客服会话附件上传能力。文件通过 Presigned URL 直接上传至 S3，数据库保存 `bucket` 与 `object_key`。

需要在 `backend/.env` 配置：

```env
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=project-kizuna-files
S3_UPLOAD_EXPIRES_SECONDS=900
```

同时需要为 EC2 或 IAM 用户配置 S3 PutObject/GetObject 权限，并在 Bucket 中配置允许前端域名 PUT 的 CORS。


## v0.1.5

新增 KZ-009 回复模板：模板 CRUD、分类筛选、启用/停用、Workspace 快捷套用模板。

## Production Deploy

```bash
cd /www/wwwroot/project-kizuna.mychisyou.com
./scripts/deploy-production.sh
```

## Alembic Baseline

First time after v0.3.0 deploy:

```bash
docker compose exec -T backend alembic -c alembic.ini stamp head
```
