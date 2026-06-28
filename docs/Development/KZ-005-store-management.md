# KZ-005 店铺管理

## 目标

让用户可以在系统中维护 Amazon JP 多店铺基础资料，为后续消息、订单、S3 附件路径和 Amazon API 授权做准备。

## V1 范围

- 店铺列表
- 新增店铺
- 编辑店铺
- 启用/停用店铺
- 删除店铺
- 搜索店铺
- 固定平台：Amazon
- 固定站点：JP

## 字段

- 店铺名称 `store_name`
- 店铺编码 `store_code`
- 平台 `platform`
- 站点 `marketplace`
- Seller ID `seller_id`
- 状态 `status`
- 备注 `note`

## 设计决策

1. V1 不接 Amazon 授权，只预留 Seller ID。
2. 店铺编码作为内部稳定识别符，建议使用 JP01、JP02、JP03。
3. 已有关联数据的店铺不建议删除，优先停用。
4. 店铺管理保持简单，不加入复杂权限和多租户逻辑。

## API

- `GET /api/v1/stores`
- `POST /api/v1/stores`
- `PUT /api/v1/stores/{store_id}`
- `DELETE /api/v1/stores/{store_id}`

## 验收标准

- 登录后可以进入 Stores 页面。
- 可以新增一个店铺，并在列表显示。
- 可以编辑店铺名称、编码、Seller ID、状态和备注。
- 可以启用/停用店铺。
- 可以按名称、编码、Seller ID 搜索。
- 删除失败时给出提示，建议停用。
