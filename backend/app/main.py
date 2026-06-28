from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1 import ai, attachments, auth, conversations, dashboard, messages, stores, templates
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import *  # noqa
from app.models import ReplyTemplate, Role, Store, User

Base.metadata.create_all(bind=engine)


def seed_defaults() -> None:
    db: Session = SessionLocal()
    try:
        if not db.query(Role).filter(Role.code == "admin").first():
            db.add_all([
                Role(name="管理员", code="admin", description="系统管理员"),
                Role(name="客服人员", code="staff", description="日常客服处理"),
            ])
            db.commit()
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(
                username="admin",
                email="admin@example.local",
                password_hash=get_password_hash("admin123456"),
                full_name="Project Kizuna Admin",
                role="admin",
                status="active",
                must_change_password=True,
            ))
            db.commit()
        if not db.query(Store).first():
            db.add(Store(store_name="Amazon JP 01", store_code="JP01", platform="Amazon", marketplace="JP", status="active"))
            db.commit()

        if not db.query(ReplyTemplate).first():
            db.add_all([
                ReplyTemplate(
                    category="配送未到",
                    title="配送状況確認",
                    content_ja="お問い合わせありがとうございます。配送状況を確認いたしますので、今しばらくお待ちいただけますでしょうか。確認後、改めてご案内いたします。",
                    content_zh="用于买家询问商品未到时，先安抚并说明会确认配送状况。",
                    risk_level="low",
                    is_active=True,
                ),
                ReplyTemplate(
                    category="商品破损",
                    title="破損写真依頼",
                    content_ja="この度はご迷惑をおかけし誠に申し訳ございません。商品の状態を確認させていただきたく、破損部分のお写真をお送りいただけますでしょうか。確認後、早急に対応いたします。",
                    content_zh="用于破损场景，要求客户发送照片后再判断补发/退款。",
                    risk_level="medium",
                    is_active=True,
                ),
                ReplyTemplate(
                    category="返品希望",
                    title="返品手続き案内",
                    content_ja="返品をご希望とのこと承知いたしました。恐れ入りますが、Amazonの注文履歴より返品手続きをお進めいただけますでしょうか。確認でき次第、順次対応いたします。",
                    content_zh="用于买家希望退货时，引导从 Amazon 订单履历发起。",
                    risk_level="medium",
                    is_active=True,
                ),
            ])
            db.commit()
    finally:
        db.close()


seed_defaults()

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(stores.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(attachments.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
