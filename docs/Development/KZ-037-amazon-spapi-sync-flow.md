# KZ-037 Amazon SP-API 同步流程增强

## 目标

把 v0.3.4.1 的正式连接能力推进到可用于生产测试的同步流程：

Amazon Orders API → Kizuna orders → Kizuna work items → 客服处理。

## 设计

- 同步入口仍然放在 `/amazon`。
- 每次同步创建一条 `amazon_sync_runs` 记录。
- 使用可控的 `days / max_results / page_limit` 限制同步范围。
- 已存在的 Amazon Order ID 不重复创建工作项。
- 如果订单状态变化，则向工作项写入系统消息和事件。
- 同步失败写入 `amazon_sync_runs.error_message` 和 `audit_logs`。

## 暂不做

- 不做定时自动同步。
- 不自动发送 Amazon 买家消息。
- 不把 Seller Central 站内信收件箱当成可自动读取数据源。
