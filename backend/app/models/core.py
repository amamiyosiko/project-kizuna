from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(100))
    role_id = Column(Integer, ForeignKey("roles.id"))
    status = Column(String(30), default="active")
    role = Column(String(30), default="staff")
    must_change_password = Column(Boolean, default=False)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    store_name = Column(String(150), nullable=False)
    store_code = Column(String(80), unique=True, nullable=False, index=True)
    platform = Column(String(50), default="Amazon")
    marketplace = Column(String(50), default="JP")
    seller_id = Column(String(150))
    status = Column(String(30), default="active")
    note = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(50), default="JP")
    buyer_name = Column(String(150))
    buyer_email_masked = Column(String(255))
    amazon_buyer_id = Column(String(255))
    total_orders = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    risk_level = Column(String(30), default="low")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    order_no = Column(String(150), index=True)
    amazon_order_id = Column(String(150), index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_status = Column(String(80))
    fulfillment_type = Column(String(50))
    purchase_date = Column(DateTime)
    shipment_status = Column(String(80))
    delivery_status = Column(String(80))
    delivery_company = Column(String(100))
    tracking_no = Column(String(150))
    estimated_delivery_date = Column(Date)
    total_amount = Column(Numeric(12, 2))
    currency = Column(String(10), default="JPY")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    conversation_no = Column(String(150))
    subject = Column(String(255))
    status = Column(String(50), default="open")
    category = Column(String(80))
    risk_level = Column(String(30), default="low")
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    last_message_at = Column(DateTime)
    last_reply_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender_type = Column(String(30), nullable=False)
    message_type = Column(String(30), default="text")
    content = Column(Text, nullable=False)
    original_language = Column(String(20), default="ja")
    translated_content = Column(Text)
    has_attachment = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class AIReply(Base):
    __tablename__ = "ai_replies"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    message_id = Column(Integer, ForeignKey("messages.id"))
    detected_category = Column(String(80))
    detected_intent = Column(Text)
    risk_level = Column(String(30))
    ai_reply_text = Column(Text, nullable=False)
    final_reply_text = Column(Text)
    confidence_score = Column(Numeric(5, 2))
    status = Column(String(30), default="draft")
    model_name = Column(String(100))
    created_by = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class ReplyTemplate(Base):
    __tablename__ = "reply_templates"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(80))
    title = Column(String(150), nullable=False)
    content_ja = Column(Text, nullable=False)
    content_zh = Column(Text)
    risk_level = Column(String(30), default="low")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_ext = Column(String(30))
    content_type = Column(String(120))
    file_size = Column(Integer, default=0)
    bucket = Column(String(255), nullable=False)
    object_key = Column(Text, nullable=False)
    status = Column(String(30), default="uploaded")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
