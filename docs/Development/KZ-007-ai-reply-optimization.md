# KZ-007 AI 回复优化

版本：v0.1.3

## 目标

把 Workspace 中的 AI 回复从简单模板升级为可追溯的售后回复引擎，支持分类、意图、风险、置信度和不同回复语气。

## 本次范围

- 规则优先的日语售后分类器
- 统一返回：category / detected_intent / risk_level / confidence_score / recommended_action
- 回复生成支持语气：标准礼貌、加强道歉、简短回复
- AI Reply 保存 detected_intent
- Workspace 显示 Intent 与 AI 判断依据

## 暂不做

- 直接调用 OpenAI 生成正式回复
- RAG 知识库检索
- 自动发送 Amazon 消息
- 订单/物流实时查询

## 设计原因

Sprint 1 的目标是尽快可用，因此先采用稳定、可追溯的规则模板，降低误回复风险。等 Workspace 跑通后，再逐步引入 OpenAI、知识库和 Amazon API。

## 验收标准

1. 客服在 Workspace 选择一条消息。
2. 点击生成 AI 日语回复。
3. 系统返回分类、Intent、风险、置信度和日语回复草稿。
4. 客服可选择语气并重新生成。
5. 客服可复制或标记完成。
