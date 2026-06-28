from __future__ import annotations

from app.ai.classifier import simple_classify


def _signature() -> str:
    return "\n\n何卒よろしくお願いいたします。"


REPLY_TEMPLATES: dict[str, str] = {
    "配送未到": (
        "お問い合わせありがとうございます。\n\n"
        "商品のお届けについてご心配をおかけしており、申し訳ございません。\n"
        "現在、配送状況を確認させていただいております。確認が取れ次第、改めてご案内いたします。\n\n"
        "恐れ入りますが、今しばらくお待ちくださいますようお願いいたします。"
    ),
    "商品破损": (
        "この度は商品に不具合があったとのこと、ご迷惑をおかけし誠に申し訳ございません。\n\n"
        "状況を確認させていただきたいため、破損箇所が分かるお写真をお送りいただけますでしょうか。\n"
        "確認後、交換または返金など、適切な対応方法をご案内いたします。"
    ),
    "返品希望": (
        "お問い合わせありがとうございます。\n\n"
        "返品をご希望とのこと、承知いたしました。\n"
        "恐れ入りますが、ご注文内容と商品の状態を確認のうえ、返品手続きについてご案内いたします。\n\n"
        "Amazonの購入履歴から返品手続きを進めていただける場合もございますので、あわせてご確認ください。"
    ),
    "缺件": (
        "この度はご迷惑をおかけし、誠に申し訳ございません。\n\n"
        "不足している部品または商品内容を確認させていただきたいため、届いた商品の全体写真と不足している内容をお知らせいただけますでしょうか。\n"
        "確認後、対応方法をご案内いたします。"
    ),
    "错发": (
        "この度はご注文内容と異なる商品が届いたとのこと、ご迷惑をおかけし誠に申し訳ございません。\n\n"
        "確認のため、届いた商品の写真、ラベル、またはパッケージが分かるお写真をお送りいただけますでしょうか。\n"
        "確認後、早急に対応方法をご案内いたします。"
    ),
    "使用方法": (
        "お問い合わせありがとうございます。\n\n"
        "ご使用方法について確認のうえ、分かりやすくご案内いたします。\n"
        "恐れ入りますが、どの部分の操作でお困りか、もう少し詳しくお知らせいただけますでしょうか。"
    ),
    "感谢/普通咨询": (
        "ご連絡ありがとうございます。\n\n"
        "ご確認いただきありがとうございます。\n"
        "また何かご不明な点がございましたら、お気軽にお問い合わせください。"
    ),
    "其他": (
        "お問い合わせありがとうございます。\n\n"
        "いただいた内容を確認のうえ、順次ご案内いたします。\n"
        "恐れ入りますが、今しばらくお待ちくださいますようお願いいたします。"
    ),
}


def generate_rule_based_reply(message: str, tone: str = "polite") -> dict:
    """Generate traceable Japanese customer-service reply.

    Sprint 1 uses stable rule templates so the seller can safely test the workflow
    before Amazon API / knowledge-base integration.
    """
    result = simple_classify(message)
    category = result["category"]
    reply = REPLY_TEMPLATES.get(category, REPLY_TEMPLATES["其他"])

    if tone == "apology" and "申し訳ございません" not in reply:
        reply = "ご迷惑をおかけしており、誠に申し訳ございません。\n\n" + reply
    elif tone == "short":
        reply = reply.replace("\n\n", "\n")

    return {
        **result,
        "reply": reply + _signature(),
        "tone": tone,
    }
