from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.ai.reply_generator import generate_rule_based_reply
from app.core.config import settings
from app.services.app_config import get_config_value_fresh

logger = logging.getLogger(__name__)


def _cfg(key: str, default: str | None = None) -> str:
    return get_config_value_fresh(key, default)


def _openai_key() -> str:
    return _cfg("OPENAI_API_KEY", settings.OPENAI_API_KEY or "")


def _openai_model() -> str:
    return _cfg("OPENAI_MODEL", settings.OPENAI_MODEL) or settings.OPENAI_MODEL


def _gemini_key() -> str:
    return _cfg("GEMINI_API_KEY", settings.GEMINI_API_KEY or "")


def _gemini_model() -> str:
    return _cfg("GEMINI_MODEL", settings.GEMINI_MODEL) or settings.GEMINI_MODEL


def _default_provider() -> str:
    return _cfg("AI_PROVIDER", settings.AI_PROVIDER) or settings.AI_PROVIDER

SUPPORTED_PROVIDERS = {"auto", "openai", "gemini", "rule"}


@dataclass(frozen=True)
class AIContext:
    ticket_no: str | None = None
    buyer_name: str | None = None
    order_no: str | None = None
    asin: str | None = None
    sku: str | None = None
    subject: str | None = None
    category: str | None = None
    risk_level: str | None = None


def _safe_json_loads(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty AI response")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("AI response is not a JSON object")
    return parsed


def _normalize_provider(provider: str | None) -> str:
    value = (provider or "auto").strip().lower()
    return value if value in SUPPORTED_PROVIDERS else "auto"


def _tone_label(tone: str) -> str:
    return {
        "polite": "標準的で丁寧",
        "apology": "謝罪をやや強める",
        "short": "簡潔",
    }.get(tone, "標準的で丁寧")


def _build_prompt(message: str, tone: str, context: AIContext | None = None) -> str:
    context = context or AIContext()
    context_lines = [
        f"工单编号: {context.ticket_no or '-'}",
        f"买家名: {context.buyer_name or '-'}",
        f"订单号: {context.order_no or '-'}",
        f"ASIN: {context.asin or '-'}",
        f"SKU: {context.sku or '-'}",
        f"主题: {context.subject or '-'}",
        f"当前分类: {context.category or '-'}",
        f"当前风险: {context.risk_level or '-'}",
    ]
    return f"""
你是日本 Amazon 店铺的客服回复助手。请根据买家消息生成可由客服确认后发送的日文回复草稿。

严格要求：
- 只输出 JSON，不要输出 Markdown。
- 不能承诺退款、补发、赔偿、取消，除非消息中已明确说明平台已完成。
- 如果事实不明，只能说会确认，不能编造物流、库存、订单状态。
- 回复语言必须是自然、礼貌的日文。
- 分类和风险请用中文字段值，便于内部客服识别。

可用分类：配送未到、配送延迟、商品破损、商品不良、缺件、错发、返品希望、退款咨询、使用方法、差评风险、感谢/普通咨询、其他
风险等级：low、medium、high
回复语气：{_tone_label(tone)}

当前工作项信息：
{chr(10).join(context_lines)}

买家最新消息：
{message}

请输出下面 JSON 结构：
{{
  "category": "配送未到",
  "detected_intent": "物流状况确认",
  "risk_level": "medium",
  "confidence_score": 88,
  "recommended_action": "客服先确认订单和物流状态，再回复买家。",
  "auto_reply_allowed": false,
  "reason": "买家询问商品是否未送达，尚未接入真实物流状态。",
  "reply": "日文客服回复草稿"
}}
""".strip()


def _normalize_result(parsed: dict[str, Any], message: str, tone: str, provider: str, model: str) -> dict[str, Any]:
    fallback = generate_rule_based_reply(message, tone=tone)
    category = str(parsed.get("category") or fallback.get("category") or "其他")
    risk_level = str(parsed.get("risk_level") or fallback.get("risk_level") or "low").lower()
    if risk_level not in {"low", "medium", "high"}:
        risk_level = fallback.get("risk_level") or "low"
    try:
        confidence = float(parsed.get("confidence_score", fallback.get("confidence_score", 70)))
    except (TypeError, ValueError):
        confidence = float(fallback.get("confidence_score", 70) or 70)
    confidence = max(0.0, min(100.0, confidence))
    reply = str(parsed.get("reply") or parsed.get("reply_text") or fallback.get("reply") or "").strip()
    if not reply:
        reply = fallback["reply"]
    return {
        "category": category,
        "detected_intent": str(parsed.get("detected_intent") or fallback.get("detected_intent") or ""),
        "risk_level": risk_level,
        "confidence_score": confidence,
        "recommended_action": str(parsed.get("recommended_action") or fallback.get("recommended_action") or "客服人工确认后回复。"),
        "auto_reply_allowed": bool(parsed.get("auto_reply_allowed", False)),
        "reason": str(parsed.get("reason") or f"由 {provider} 生成；客服发送前需要确认。"),
        "reply": reply,
        "tone": tone,
        "provider": provider,
        "model": model,
        "fallback_used": False,
    }


def _rule_reply(message: str, tone: str, reason: str | None = None) -> dict[str, Any]:
    generated = generate_rule_based_reply(message, tone=tone)
    return {
        **generated,
        "provider": "rule",
        "model": "rule-based",
        "fallback_used": True,
        "reason": reason or generated.get("reason") or "未配置可用 AI Provider，已使用本地规则回复。",
    }


def _generate_openai(message: str, tone: str, context: AIContext | None = None) -> dict[str, Any]:
    api_key = _openai_key()
    model = _openai_model()
    if not api_key or api_key in {"your_openai_api_key", "你的真实key"}:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI

    prompt = _build_prompt(message, tone, context)
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a safe Japanese Amazon customer support reply assistant. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    parsed = _safe_json_loads(content)
    return _normalize_result(parsed, message, tone, "openai", model)


def _generate_gemini(message: str, tone: str, context: AIContext | None = None) -> dict[str, Any]:
    api_key = _gemini_key()
    if not api_key or api_key in {"your_gemini_api_key", "你的gemini真实key"}:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    prompt = _build_prompt(message, tone, context)
    model = _gemini_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1200,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini API error {exc.code}: {detail[:300]}") from exc
    data = json.loads(raw)
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    content = "".join(str(part.get("text", "")) for part in parts)
    parsed = _safe_json_loads(content)
    return _normalize_result(parsed, message, tone, "gemini", model)


def generate_ai_customer_reply(
    message: str,
    tone: str = "polite",
    provider: str | None = "auto",
    context: AIContext | None = None,
) -> dict[str, Any]:
    requested = _normalize_provider(provider or _default_provider())
    if requested == "rule":
        return _rule_reply(message, tone, "已手动选择备用规则回复。")

    if requested == "openai":
        try:
            return _generate_openai(message, tone, context)
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI reply generation failed")
            return _rule_reply(message, tone, f"OpenAI 调用失败，已降级备用规则：{exc}")

    if requested == "gemini":
        try:
            return _generate_gemini(message, tone, context)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini reply generation failed")
            return _rule_reply(message, tone, f"Gemini 调用失败，已降级备用规则：{exc}")

    # auto: prefer configured default, then try the other provider, then rule.
    preferred = _normalize_provider(_default_provider())
    order = [preferred] if preferred in {"openai", "gemini"} else []
    for candidate in ["openai", "gemini"]:
        if candidate not in order:
            order.append(candidate)
    errors: list[str] = []
    for candidate in order:
        try:
            if candidate == "openai":
                return _generate_openai(message, tone, context)
            if candidate == "gemini":
                return _generate_gemini(message, tone, context)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s reply generation failed: %s", candidate, exc)
            errors.append(f"{candidate}: {exc}")
    return _rule_reply(message, tone, " / ".join(errors) or "未配置 AI API Key，已使用备用规则回复。")
