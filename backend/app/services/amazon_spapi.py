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


def marketplace_id() -> str:
    return (settings.AMAZON_MARKETPLACE_ID or "A1VC38T7YXB528").strip()


def spapi_region() -> str:
    return (settings.AMAZON_REGION or "jp").strip().lower()


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


def get_lwa_access_token() -> dict[str, Any]:
    required = {
        "AMAZON_LWA_CLIENT_ID": settings.AMAZON_LWA_CLIENT_ID,
        "AMAZON_LWA_CLIENT_SECRET": settings.AMAZON_LWA_CLIENT_SECRET,
        "AMAZON_REFRESH_TOKEN": settings.AMAZON_REFRESH_TOKEN,
    }
    missing = [k for k, v in required.items() if not has_real_value(v)]
    if missing:
        raise AmazonSPAPIError("缺少 LWA 配置：" + ", ".join(missing))

    resp = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": settings.AMAZON_REFRESH_TOKEN,
            "client_id": settings.AMAZON_LWA_CLIENT_ID,
            "client_secret": settings.AMAZON_LWA_CLIENT_SECRET,
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
) -> dict[str, Any]:
    endpoint = endpoint_for_region()
    token = get_lwa_access_token()["access_token"]
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {
        "host": urlparse(endpoint).netloc,
        "user-agent": "ProjectKizuna/0.3.4.1 (Language=Python/3.12)",
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


def get_recent_orders(days: int = 3, max_results: int = 20) -> dict[str, Any]:
    days = min(max(days, 1), 30)
    max_results = min(max(max_results, 1), 100)
    created_after = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return call_spapi(
        "GET",
        "/orders/v0/orders",
        params={
            "MarketplaceIds": marketplace_id(),
            "CreatedAfter": created_after,
            "MaxResultsPerPage": max_results,
        },
    )


def get_messaging_actions_for_order(amazon_order_id: str) -> dict[str, Any]:
    return call_spapi(
        "GET",
        f"/messaging/v1/orders/{amazon_order_id}/messages",
        params={"marketplaceIds": marketplace_id()},
    )


def configuration_overview() -> dict[str, Any]:
    endpoint = endpoint_for_region()
    creds = boto3.Session().get_credentials()
    return {
        "marketplace_id": marketplace_id(),
        "endpoint_region": spapi_region(),
        "endpoint": endpoint,
        "signing_region": signing_region_for_endpoint(endpoint),
        "lwa_ready": all(has_real_value(v) for v in [settings.AMAZON_LWA_CLIENT_ID, settings.AMAZON_LWA_CLIENT_SECRET, settings.AMAZON_REFRESH_TOKEN]),
        "aws_signing_ready": bool(creds),
    }
