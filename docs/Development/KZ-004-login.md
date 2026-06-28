# KZ-004 登录系统

## 目标

用户可以使用默认管理员账号登录 Project Kizuna，并进入客服工作台。

## 验收标准

1. `docker compose up` 可以启动前后端。
2. 打开 `http://localhost:3000` 自动进入登录页。
3. 使用 `admin / admin123456` 可以登录。
4. 首次登录提示修改密码。
5. 修改密码后进入 `/workspace`。
6. Workspace 可以通过 token 调用 `/auth/me`。

## 暂不做

- 多角色复杂权限
- 账号邀请
- 邮箱验证
- 双因素认证
