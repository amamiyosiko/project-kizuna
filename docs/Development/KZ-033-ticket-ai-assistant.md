# KZ-033 Ticket AI Assistant

## 背景

v0.3.1 完成工作项中心，v0.3.2 完成 S3 附件上传。v0.3.3 只处理一个目标：把 AI 回复草稿接入工作项详情。

## 设计原则

- AI 只生成草稿，不直接发送给买家。
- 客服必须人工确认、编辑后才能保存。
- 当前版本使用可追踪的规则模板，保证生产测试稳定。
- 后续接入 OpenAI、知识库和 Amazon SP-API 时保持接口形状兼容。

## 接口

`POST /api/v1/ai/tickets/{ticket_id}/generate-reply`

请求：

```json
{
  "tone": "polite"
}
```

返回：

```json
{
  "ticket_id": 1,
  "source_message_id": 1,
  "category": "配送未到",
  "detected_intent": "物流状况确认",
  "risk_level": "medium",
  "confidence_score": 88,
  "recommended_action": "确认订单和物流状态；未接入 Amazon API 前，先引导人工确认配送状况。",
  "auto_reply_allowed": true,
  "reason": "命中关键词：配送",
  "tone": "polite",
  "reply_text": "...",
  "source_excerpt": "..."
}
```

## 前端工作流

1. 选择工作项。
2. AI 使用最新 `CUSTOMER` 消息生成日文草稿。
3. 客服可以：
   - 填入客服回复框；
   - 保存为 AI 消息到时间线；
   - 应用分类/风险。

## 数据库

本版本不新增表，不需要 Alembic migration。

