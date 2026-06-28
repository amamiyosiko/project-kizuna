# KZ-021 Ticket Workspace

## 目标

让客服可以在 Project Kizuna 内创建、查看、处理真实 Ticket，而不是使用 Demo 消息。

## 核心模型

- Ticket：一个客户问题/售后事项。
- TicketMessage：Ticket 下的多轮消息。
- TicketEvent：Ticket 的业务时间轴。

## 状态

- NEW
- OPEN
- PROCESSING
- WAITING_CUSTOMER
- WAITING_PLATFORM
- RESOLVED
- CLOSED

## 优先级

- P1：紧急，差评/退款/账号风险
- P2：高，重要售后问题
- P3：普通
- P4：低

## 验收标准

- 可以新建 Ticket。
- 可以在左侧列表看到 Ticket。
- 可以打开 Ticket 查看买家消息。
- 可以保存客服回复。
- 可以修改状态和优先级。
- 可以看到 Timeline。
