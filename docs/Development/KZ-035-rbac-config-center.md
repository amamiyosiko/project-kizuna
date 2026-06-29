# KZ-035 RBAC + Config Center

## 权限模型

当前采用一个账号归属一个角色的 RBAC 模型：

```text
User → Role → Permission
```

后续如有需要，可以扩展为一个账号多个角色。

## 内置角色

- super_admin：超级管理员，拥有全部权限。
- admin：管理员，维护业务配置、同步和日志。
- manager：主管，处理工作项、风险和审核。
- agent：客服，处理日常工作项、附件和 AI 回复。

## 配置中心

配置中心中的密钥使用 `CONFIG_ENCRYPTION_KEY` 或 `JWT_SECRET_KEY` 派生密钥加密保存。建议生产环境在 `.env` 中设置固定的 `CONFIG_ENCRYPTION_KEY`。

## 部署注意

本版本依赖数据库迁移。现有生产库升级时，需要执行：

```bash
docker compose exec -T backend alembic -c alembic.ini upgrade head
docker compose restart backend
```

如果 backend 在迁移前已启动，可能会暂时跳过 RBAC seed；迁移完成后重启 backend 即可自动写入内置角色和权限。
