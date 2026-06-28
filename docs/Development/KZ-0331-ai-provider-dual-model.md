# KZ-0331 AI Provider 双模型

## 范围

本次只围绕工作项中心的 AI 回复助手，不新增其它业务模块。

## 设计

后端新增统一 AI Provider 层：

```text
工作项消息
  ↓
AI Provider
  ├── OpenAI GPT
  ├── Google Gemini
  └── Rule-based fallback
  ↓
日文客服回复草稿
```

## 安全原则

- AI 只生成草稿，不自动发送 Amazon。
- 客服必须确认后才保存回复。
- 不确定的订单、物流、退款、补发状态不能让 AI 直接承诺。
- API 调用失败时降级为备用规则，保证客服页面可用。

## 验收

1. 工作项详情右侧显示 AI 回复助手。
2. 模型可选择：自动、GPT、Gemini、备用规则。
3. 选择备用规则可以不配置 API Key 生成回复。
4. 配置 OpenAI Key 后，选择 GPT 可以生成回复。
5. 配置 Gemini Key 后，选择 Gemini 可以生成回复。
6. AI 结果显示 Provider、模型和判断依据。
