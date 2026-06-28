# KZ-009 回复模板

版本：v0.1.5

## 目标

让客服可以维护常用日语售后回复，并在 Customer Workspace 中按当前会话分类快速套用。

## 范围

- 回复模板 CRUD
- 按售后分类筛选模板
- 启用 / 停用模板
- Workspace 快捷模板区域
- 默认内置 3 个 Amazon JP 售后模板

## 不包含

- 模板变量渲染
- 模板审批流
- 多语言模板版本管理
- Prompt A/B Test

## 后端接口

- `GET /api/v1/templates`
- `GET /api/v1/templates?category=配送未到`
- `GET /api/v1/templates?active_only=true`
- `POST /api/v1/templates`
- `PUT /api/v1/templates/{id}`
- `DELETE /api/v1/templates/{id}`

## 验收标准

1. 可以新增、编辑、删除模板。
2. 可以停用模板，停用后 Workspace 不显示。
3. Workspace 会根据当前会话分类显示可用模板。
4. 点击模板后，日语内容写入回复草稿框。
