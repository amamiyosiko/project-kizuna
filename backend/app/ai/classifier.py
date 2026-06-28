from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryRule:
    category: str
    intent: str
    risk_level: str
    confidence: float
    keywords: tuple[str, ...]
    recommended_action: str
    auto_reply_allowed: bool


CATEGORY_RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        category="配送未到",
        intent="物流状况确认",
        risk_level="medium",
        confidence=88.0,
        keywords=("届か", "届きません", "まだ", "配送", "配達", "遅", "発送", "追跡", "どこ", "到着"),
        recommended_action="确认订单和物流状态；未接入 Amazon API 前，先引导人工确认配送状况。",
        auto_reply_allowed=True,
    ),
    CategoryRule(
        category="商品破损",
        intent="破损照片确认",
        risk_level="high",
        confidence=91.0,
        keywords=("破損", "壊", "割れ", "傷", "キズ", "へこ", "不良", "使え", "壊れて"),
        recommended_action="先表达歉意，要求客户提供破损位置照片，再人工判断补发或退款。",
        auto_reply_allowed=False,
    ),
    CategoryRule(
        category="返品希望",
        intent="退货流程说明",
        risk_level="high",
        confidence=86.0,
        keywords=("返品", "返金", "キャンセル", "返したい", "払い戻し"),
        recommended_action="先确认退货意向和订单状态，引导客户按 Amazon 退货流程处理。",
        auto_reply_allowed=False,
    ),
    CategoryRule(
        category="缺件",
        intent="缺少部件确认",
        risk_level="medium",
        confidence=84.0,
        keywords=("足り", "不足", "入ってい", "入ってな", "部品", "付属品", "一部"),
        recommended_action="确认缺少的具体部件和商品照片，再决定补发或其他处理。",
        auto_reply_allowed=False,
    ),
    CategoryRule(
        category="错发",
        intent="商品差异确认",
        risk_level="medium",
        confidence=83.0,
        keywords=("違", "サイズ", "色", "カラー", "別の商品", "注文と違う", "数量"),
        recommended_action="要求客户提供商品照片/标签/包装信息，核对订单后再处理。",
        auto_reply_allowed=False,
    ),
    CategoryRule(
        category="使用方法",
        intent="使用方法说明",
        risk_level="low",
        confidence=78.0,
        keywords=("使い方", "使用方法", "説明", "設定", "取り付け", "組み立て"),
        recommended_action="根据商品说明或模板回复；如果不确定，转人工确认。",
        auto_reply_allowed=True,
    ),
    CategoryRule(
        category="感谢/普通咨询",
        intent="普通确认回复",
        risk_level="low",
        confidence=75.0,
        keywords=("ありがとう", "ありがとうございます", "確認", "了解", "分かりました"),
        recommended_action="礼貌回复并关闭或继续跟进。",
        auto_reply_allowed=True,
    ),
)


def _contains_any(message: str, keywords: tuple[str, ...]) -> bool:
    normalized = message.lower().replace(" ", "")
    return any(keyword.lower().replace(" ", "") in normalized for keyword in keywords)


def simple_classify(message: str) -> dict:
    """Rule-first classifier for Sprint 1.

    KZ-007 intentionally keeps this deterministic and traceable. Later versions can
    call an LLM, but the response shape should stay compatible.
    """
    clean = (message or "").strip()
    if not clean:
        return {
            "category": "其他",
            "detected_intent": "空消息",
            "risk_level": "low",
            "confidence_score": 40.0,
            "recommended_action": "请录入买家消息后再生成回复。",
            "auto_reply_allowed": False,
            "reason": "消息内容为空，无法判断。",
        }

    for rule in CATEGORY_RULES:
        if _contains_any(clean, rule.keywords):
            matched = [kw for kw in rule.keywords if kw.lower().replace(" ", "") in clean.lower().replace(" ", "")]
            return {
                "category": rule.category,
                "detected_intent": rule.intent,
                "risk_level": rule.risk_level,
                "confidence_score": rule.confidence,
                "recommended_action": rule.recommended_action,
                "auto_reply_allowed": rule.auto_reply_allowed,
                "reason": f"命中关键词：{', '.join(matched[:5])}",
            }

    return {
        "category": "其他",
        "detected_intent": "人工确认",
        "risk_level": "low",
        "confidence_score": 58.0,
        "recommended_action": "未识别为常见售后类型，建议人工确认后回复。",
        "auto_reply_allowed": False,
        "reason": "未命中 Sprint 1 售后关键词规则。",
    }
