# KZ-022 Login Security

## 目标

移除登录页和首次修改密码页中的默认账号/密码展示，避免生产环境暴露默认凭据。

## 变更

- `frontend/app/login/page.tsx`
  - 用户名默认值改为空。
  - 密码默认值改为空。
  - 删除默认账号提示。
- `frontend/app/profile/page.tsx`
  - 旧密码默认值改为空。
- `frontend/package.json`
  - 增加 `@swc/helpers` 依赖。
