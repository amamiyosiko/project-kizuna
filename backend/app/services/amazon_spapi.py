from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

from app.core.config import settings
from app.services.app_config import get_config_value_fresh


class AmazonSPAPIError(Exception):
    """Raised when Amazon SP-API or LWA returns an error."""


PLACEHOLDERS = {
    "",
    "your_lwa_client_id",
    "your_lwa_client_secret",
    "your_refresh_token",
    "your_marketplace_id",
    "你的lwa_client_id",
    "你的lwa_client_secret",
    "你的refresh_token",
    "你的marketplace_id",
}


def has_real_value(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip() not in PLACEHOLDERS)


def _cfg(key: str, default: str | None = None) -> str:
    return get_config_value_fresh(key, default)


def marketplace_id(value: str | None = None) -> str:
    if value and value.strip():
        return value.strip()
    return (_cfg("AMAZON_MARKETPLACE_ID", settings.AMAZON_MARKETPLACE_ID or "A1VC38T7YXB528") or "A1VC38T7YXB528").strip()


def spapi_region() -> str:
    return (_cfg("AMAZON_REGION", settings.AMAZON_REGION or "jp") or "jp").strip().lower()


def endpoint_for_region(region: str | None = None) -> str:
    r = (region or spapi_region()).lower()
    if r in {"jp", "fe", "far_east", "far-east", "sg", "au"}:
        return "https://sellingpartnerapi-fe.amazon.com"
    if r in {"eu", "uk", "de", "fr", "it", "es"}:
        return "https://sellingpartnerapi-eu.amazon.com"
    return "https://sellingpartnerapi-na.amazon.com"


def signing_region_for_endpoint(endpoint: str) -> str:
    host = urlparse(endpoint).netloc
    if "-fe." in host:
        return "us-west-2"
    if "-eu." in host:
        return "eu-west-1"
    return "us-east-1"


def get_lwa_access_token(refresh_token_override: str | None = None) -> dict[str, Any]:
    client_id = _cfg("AMAZON_LWA_CLIENT_ID", settings.AMAZON_LWA_CLIENT_ID or "")
    client_secret = _cfg("AMAZON_LWA_CLIENT_SECRET", settings.AMAZON_LWA_CLIENT_SECRET or "")
    refresh_token = refresh_token_override or _cfg("AMAZON_REFRESH_TOKEN", settings.AMAZON_REFRESH_TOKEN or "")
    required = {
        "AMAZON_LWA_CLIENT_ID": client_id,
        "AMAZON_LWA_CLIENT_SECRET": client_secret,
        "AMAZON_REFRESH_TOKEN": refresh_token,
    }
    missing = [k for k, v in required.items() if not has_real_value(v)]
    if missing:
        raise AmazonSPAPIError("缺少 LWA 配置：" + ", ".join(missing))

    resp = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise AmazonSPAPIError(f"LWA 获取 access token 失败：{resp.status_code} {resp.text[:500]}")
    data = resp.json()
    if not data.get("access_token"):
        raise AmazonSPAPIError("LWA 响应中没有 access_token")
    return data


def _aws_credentials() -> Credentials:
    creds = boto3.Session().get_credentials()
    if not creds:
        raise AmazonSPAPIError(
            "未找到 AWS 签名凭证。请配置 SP-API 对应 IAM 凭证，或让 EC2 角色具备 SP-API 调用权限。"
        )
    frozen = creds.get_frozen_credentials()
    return Credentials(frozen.access_key, frozen.secret_key, frozen.token)


def call_spapi(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    refresh_token: str | None = None,
) -> dict[str, Any]:
    endpoint = endpoint_for_region()
    token = get_lwa_access_token(refresh_token)["access_token"]
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {
        "host": urlparse(endpoint).netloc,
        "user-agent": "ProjectKizuna/0.3.8 (Language=Python/3.12)",
        "x-amz-access-token": token,
        "accept": "application/json",
    }
    if data is not None:
        headers["content-type"] = "application/json"

    request = AWSRequest(method=method.upper(), url=f"{endpoint}{path}", params=params or {}, data=data, headers=headers)
    SigV4Auth(_aws_credentials(), "execute-api", signing_region_for_endpoint(endpoint)).add_auth(request)
    prepared = request.prepare()

    resp = requests.request(
        method.upper(),
        prepared.url,
        headers=dict(prepared.headers),
        data=data,
        timeout=30,
    )
    text = resp.text or ""
    if resp.status_code >= 400:
        raise AmazonSPAPIError(f"SP-API 请求失败：{resp.status_code} {text[:800]}")
    if not text:
        return {"status_code": resp.status_code}
    try:
        return resp.json()
    except ValueError:
        return {"status_code": resp.status_code, "raw": text[:1000]}


def get_recent_orders(days: int = 3, max_results: int = 20, marketplace_id_override: str | None = None, refresh_token: str | None = None) -> dict[str, Any]:
    days = min(max(days, 1), 30)
    max_results = min(max(max_results, 1), 100)
    created_after = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return call_spapi(
        "GET",
        "/orders/v0/orders",
        params={
            "MarketplaceIds": marketplace_id(marketplace_id_override),
            "CreatedAfter": created_after,
            "MaxResultsPerPage": max_results,
        },
        refresh_token=refresh_token,
    )


def extract_orders(data: dict[str, Any]) -> list[dict[str, Any]]:
    payload = data.get("payload") if isinstance(data, dict) else {}
    if isinstance(payload, dict) and isinstance(payload.get("Orders"), list):
        return payload.get("Orders") or []
    if isinstance(data, dict) and isinstance(data.get("Orders"), list):
        return data.get("Orders") or []
    return []


def extract_next_token(data: dict[str, Any]) -> str | None:
    payload = data.get("payload") if isinstance(data, dict) else {}
    token = None
    if isinstance(payload, dict):
        token = payload.get("NextToken") or payload.get("nextToken")
    if not token and isinstance(data, dict):
        token = data.get("NextToken") or data.get("nextToken")
    return str(token) if token else None


def get_recent_orders_pages(days: int = 3, max_results: int = 20, page_limit: int = 1, marketplace_id_override: str | None = None, refresh_token: str | None = None) -> tuple[list[dict[str, Any]], int]:
    """Fetch recent orders with limited pagination.

    Returns a tuple of (orders, pages_fetched). The page limit is intentionally
    capped to keep production sync predictable while we are still in v0.3.x.
    """
    days = min(max(days, 1), 30)
    max_results = min(max(max_results, 1), 100)
    page_limit = min(max(page_limit, 1), 10)
    created_after = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    orders: list[dict[str, Any]] = []
    next_token: str | None = None
    pages = 0
    for _ in range(page_limit):
        if next_token:
            params = {"NextToken": next_token}
        else:
            params = {
                "MarketplaceIds": marketplace_id(marketplace_id_override),
                "CreatedAfter": created_after,
                "MaxResultsPerPage": max_results,
            }
        data = call_spapi("GET", "/orders/v0/orders", params=params, refresh_token=refresh_token)
        pages += 1
        orders.extend(extract_orders(data))
        next_token = extract_next_token(data)
        if not next_token:
            break
    return orders, pages


def get_messaging_actions_for_order(amazon_order_id: str, marketplace_id_override: str | None = None, refresh_token: str | None = None) -> dict[str, Any]:
    return call_spapi(
        "GET",
        f"/messaging/v1/orders/{amazon_order_id}/messages",
        params={"marketplaceIds": marketplace_id(marketplace_id_override)},
        refresh_token=refresh_token,
    )


def configuration_overview() -> dict[str, Any]:
    endpoint = endpoint_for_region()
    creds = boto3.Session().get_credentials()
    return {
        "marketplace_id": marketplace_id(),
        "endpoint_region": spapi_region(),
        "endpoint": endpoint,
        "signing_region": signing_region_for_endpoint(endpoint),
        "lwa_ready": all(has_real_value(v) for v in [_cfg("AMAZON_LWA_CLIENT_ID", settings.AMAZON_LWA_CLIENT_ID or ""), _cfg("AMAZON_LWA_CLIENT_SECRET", settings.AMAZON_LWA_CLIENT_SECRET or ""), _cfg("AMAZON_REFRESH_TOKEN", settings.AMAZON_REFRESH_TOKEN or "")]),
        "aws_signing_ready": bool(creds),
    }
