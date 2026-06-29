from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Iterable

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import SystemConfig

SECRET_PLACEHOLDERS = {
    "",
    "your_openai_api_key",
    "your_gemini_api_key",
    "your_lwa_client_id",
    "your_lwa_client_secret",
    "your_refresh_token",
    "你的真实key",
    "你的OpenAI真实Key",
    "你的Gemini真实Key",
}

CONFIG_DEFINITIONS: dict[str, dict[str, str | bool]] = {
    "AI_PROVIDER": {"group": "AI", "label": "AI 默认 Provider", "secret": False, "env": "AI_PROVIDER"},
    "OPENAI_API_KEY": {"group": "AI", "label": "OpenAI API Key", "secret": True, "env": "OPENAI_API_KEY"},
    "OPENAI_MODEL": {"group": "AI", "label": "OpenAI Model", "secret": False, "env": "OPENAI_MODEL"},
    "GEMINI_API_KEY": {"group": "AI", "label": "Gemini API Key", "secret": True, "env": "GEMINI_API_KEY"},
    "GEMINI_MODEL": {"group": "AI", "label": "Gemini Model", "secret": False, "env": "GEMINI_MODEL"},
    "AMAZON_LWA_CLIENT_ID": {"group": "Amazon", "label": "LWA Client ID", "secret": True, "env": "AMAZON_LWA_CLIENT_ID"},
    "AMAZON_LWA_CLIENT_SECRET": {"group": "Amazon", "label": "LWA Client Secret", "secret": True, "env": "AMAZON_LWA_CLIENT_SECRET"},
    "AMAZON_REFRESH_TOKEN": {"group": "Amazon", "label": "LWA Refresh Token", "secret": True, "env": "AMAZON_REFRESH_TOKEN"},
    "AMAZON_MARKETPLACE_ID": {"group": "Amazon", "label": "Marketplace ID", "secret": False, "env": "AMAZON_MARKETPLACE_ID"},
    "AMAZON_REGION": {"group": "Amazon", "label": "Amazon Region", "secret": False, "env": "AMAZON_REGION"},
}


def _fernet() -> Fernet:
    raw = settings.CONFIG_ENCRYPTION_KEY or settings.JWT_SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Allows old/plain values if an early deployment wrote them before encryption.
        return value


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= 10:
        return value[:2] + "****"
    return f"{value[:6]}****{value[-4:]}"


def is_real_value(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip() not in SECRET_PLACEHOLDERS)


def env_value(key: str) -> str:
    definition = CONFIG_DEFINITIONS.get(key, {})
    attr = str(definition.get("env") or key)
    value = getattr(settings, attr, None)
    return "" if value is None else str(value)


def get_config_value(db: Session, key: str, default: str | None = None) -> str:
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if config:
        value = decrypt_value(config.value_encrypted) if config.is_secret else (config.value_encrypted or "")
        if value:
            return value
    env = env_value(key)
    return env if env else (default or "")


def get_config_value_fresh(key: str, default: str | None = None) -> str:
    db = SessionLocal()
    try:
        return get_config_value(db, key, default)
    finally:
        db.close()


def set_config_value(db: Session, key: str, value: str, actor_user_id: int | None = None) -> SystemConfig:
    if key not in CONFIG_DEFINITIONS:
        raise ValueError(f"unsupported config key: {key}")
    definition = CONFIG_DEFINITIONS[key]
    is_secret = bool(definition.get("secret"))
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        config = SystemConfig(key=key)
    config.group = str(definition.get("group") or "General")
    config.label = str(definition.get("label") or key)
    config.is_secret = is_secret
    config.value_encrypted = encrypt_value(value) if is_secret else value
    config.updated_by = actor_user_id
    db.add(config)
    return config


def config_overview_items(db: Session) -> list[dict[str, str | bool]]:
    items: list[dict[str, str | bool]] = []
    for key, definition in CONFIG_DEFINITIONS.items():
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        from_db = bool(config)
        is_secret = bool(definition.get("secret"))
        raw = get_config_value(db, key)
        items.append({
            "key": key,
            "group": str(definition.get("group") or "General"),
            "label": str(definition.get("label") or key),
            "is_secret": is_secret,
            "configured": is_real_value(raw) if is_secret else bool(raw),
            "value": mask_secret(raw) if is_secret else raw,
            "source": "database" if from_db else "env/default",
        })
    return items
