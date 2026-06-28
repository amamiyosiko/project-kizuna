# KZ-034 Amazon SP-API Stage 1

## 目标

在不打乱当前 v1.0 路线的前提下，先完成 Amazon 接入的基础链路：

- 确认服务器环境变量是否具备 SP-API 接入条件
- 确认 Amazon 店铺是否填写 Seller ID
- 在自动同步前，支持人工粘贴真实 Amazon 买家消息并导入为工作项

## 设计原则

- 不在前端展示任何真实密钥
- 没有凭证时不显示“自动同步”功能
- 不自动发送回复到 Amazon
- 所有买家消息先进入工作项中心，由客服和 AI 辅助处理

## 环境变量

```env
AMAZON_LWA_CLIENT_ID=
AMAZON_LWA_CLIENT_SECRET=
AMAZON_REFRESH_TOKEN=
AMAZON_MARKETPLACE_ID=
AMAZON_REGION=jp
```

## API

### GET `/api/v1/amazon/status`

返回凭证准备状态、店铺 Seller ID 状态、缺失项和下一步建议。

### POST `/api/v1/amazon/manual-import`

将人工粘贴的 Amazon 买家消息导入为工作项。

## 后续阶段

v0.3.4 只做 Stage 1。真实自动同步将在后续版本中接入：

- OAuth / refresh token 正式配置
- 拉取 Amazon 买家消息
- 根据 order / buyer / store 自动匹配或创建工作项
- 同步状态与错误日志
