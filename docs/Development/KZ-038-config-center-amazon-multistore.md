# KZ-038 配置中心重构与 Amazon 多店铺授权

## 背景

v0.3.5 的配置中心把 OpenAI、Gemini、Amazon 等配置放在同一个页面。正式使用时不利于维护，也无法清楚表达多家 Amazon 店铺各自的授权状态。

## 设计

### 配置拆分

- `/settings/ai`：AI Provider、OpenAI、Gemini。
- `/settings/amazon`：Amazon SP-API 应用级配置。
- `/stores`：每家店铺独立维护 Seller ID、Marketplace ID、Refresh Token 和同步开关。
- `/amazon`：只保留运营动作，如连接测试、同步订单、查看同步记录、手动导入。

### Amazon 配置分层

应用级：

- LWA Client ID
- LWA Client Secret
- 默认 Marketplace ID
- Amazon Region

店铺级：

- Seller ID
- Marketplace ID
- Refresh Token
- 是否启用同步
- 最后同步时间

## 安全

- Refresh Token 使用 `CONFIG_ENCRYPTION_KEY` 派生的 Fernet 密钥加密保存。
- 前端只显示是否已配置和脱敏值。
- 保存配置会写入操作日志。
