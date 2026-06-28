# KZ-0341 Amazon SP-API 正式接入基础版

## 目标

把 v0.3.4 的“准备状态 + 手动导入”升级为可以调用真实 SP-API 的生产基础版本。

## 范围

- LWA access token 获取
- AWS SigV4 签名
- Orders API 最近订单读取
- Messaging API 可发送动作查询
- 最近订单导入为工作项

## 不做

- 不自动回复 Amazon 买家
- 不自动发送消息
- 不读取受限 PII
- 不做后台定时同步

## 环境变量

```env
AMAZON_LWA_CLIENT_ID=
AMAZON_LWA_CLIENT_SECRET=
AMAZON_REFRESH_TOKEN=
AMAZON_MARKETPLACE_ID=A1VC38T7YXB528
AMAZON_REGION=jp
```

如果 EC2 IAM Role 不能用于 SP-API 签名，需要再补充 SP-API 对应 IAM 凭证：

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
```

## 验收

1. 打开 `/amazon`。
2. 凭证状态显示 LWA、Refresh Token、Marketplace、AWS 签名均已配置。
3. 点击“测试 SP-API 连接”。
4. 成功后点击“同步最近订单为工作项”。
5. 在 `/workspace` 看到新建的 Amazon 订单工作项。
