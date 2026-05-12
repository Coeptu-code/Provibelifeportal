import base64
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode

import requests
from django.conf import settings


class ShopifyError(Exception):
    pass


def _normalized_shop(shop: str | None = None) -> str:
    value = (shop or settings.SHOPIFY_SHOP or "").strip().lower()
    value = re.sub(r"^https?://", "", value)
    if not value.endswith(".myshopify.com"):
        if "." not in value:
            value = f"{value}.myshopify.com"
        else:
            raise ShopifyError("SHOPIFY_SHOP must be a valid .myshopify.com domain.")
    return value


def shop_admin_url(path: str, shop: str | None = None) -> str:
    normalized = _normalized_shop(shop)
    clean_path = path.lstrip("/")
    return f"https://{normalized}/admin/api/{settings.SHOPIFY_API_VERSION}/{clean_path}"


def _headers(access_token: str | None = None) -> dict[str, str]:
    token = (access_token or settings.SHOPIFY_ACCESS_TOKEN or "").strip()
    if not token:
        try:
            from shopify_integration.models import ShopifyToken
            obj = ShopifyToken.objects.filter(shop=_normalized_shop()).first()
            if obj:
                token = obj.access_token
        except Exception:
            pass
    if not token:
        raise ShopifyError("SHOPIFY_ACCESS_TOKEN is not configured. Visit /auth/shopify/install/ to complete OAuth.")
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Shopify-Access-Token": token,
    }


def admin_rest(method: str, path: str, payload: dict | None = None, shop: str | None = None) -> dict:
    try:
        response = requests.request(
            method.upper(),
            shop_admin_url(path, shop=shop),
            headers=_headers(),
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ShopifyError(f"Shopify request failed: {exc}") from exc
    if response.status_code >= 400:
        raise ShopifyError(f"Shopify API error {response.status_code}: {response.text[:500]}")
    if not response.text.strip():
        return {}
    return response.json()


def admin_graphql(query: str, variables: dict | None = None, shop: str | None = None) -> dict:
    payload = {"query": query, "variables": variables or {}}
    data = admin_rest("POST", "graphql.json", payload=payload, shop=shop)
    if data.get("errors"):
        raise ShopifyError(f"Shopify GraphQL errors: {json.dumps(data['errors'])[:500]}")
    return data.get("data", {})


def verify_oauth_hmac(params: dict[str, str]) -> bool:
    received = params.get("hmac", "")
    if not received or not settings.SHOPIFY_CLIENT_SECRET:
        return False
    message = "&".join(
        f"{key}={value}"
        for key, value in sorted(params.items())
        if key not in {"hmac", "signature"}
    )
    digest = hmac.new(
        settings.SHOPIFY_CLIENT_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, received)


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not settings.SHOPIFY_WEBHOOK_SECRET:
        return False
    digest = hmac.new(
        settings.SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).digest()
    encoded = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(encoded, signature or "")


def build_oauth_install_url(state: str, shop: str | None = None) -> str:
    normalized = _normalized_shop(shop)
    query = {
        "client_id": settings.SHOPIFY_CLIENT_ID,
        "scope": ",".join(settings.SHOPIFY_APP_SCOPES),
        "redirect_uri": settings.SHOPIFY_REDIRECT_URI,
        "state": state,
    }
    return f"https://{normalized}/admin/oauth/authorize?{urlencode(query)}"


def exchange_code_for_token(code: str, shop: str | None = None) -> dict:
    normalized = _normalized_shop(shop)
    try:
        response = requests.post(
            f"https://{normalized}/admin/oauth/access_token",
            json={
                "client_id": settings.SHOPIFY_CLIENT_ID,
                "client_secret": settings.SHOPIFY_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ShopifyError(f"Shopify OAuth exchange failed: {exc}") from exc
    if response.status_code >= 400:
        raise ShopifyError(f"Shopify OAuth error {response.status_code}: {response.text[:500]}")
    return response.json()


def persist_access_token(access_token: str, shop: str | None = None, scopes: str | None = None) -> None:
    env_path = Path(settings.BASE_DIR) / ".env"
    current = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                current[key.strip()] = value

    current["SHOPIFY_ACCESS_TOKEN"] = access_token
    if shop:
        current["SHOPIFY_SHOP"] = _normalized_shop(shop)
    if scopes:
        current["SHOPIFY_APP_SCOPES"] = scopes

    lines = []
    seen = set()
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in raw_line and not raw_line.lstrip().startswith("#"):
                key = raw_line.split("=", 1)[0].strip()
                if key in current:
                    lines.append(f"{key}={current[key]}")
                    seen.add(key)
                else:
                    lines.append(raw_line)
            else:
                lines.append(raw_line)
    for key in ("SHOPIFY_ACCESS_TOKEN", "SHOPIFY_SHOP", "SHOPIFY_APP_SCOPES"):
        if key in current and key not in seen:
            lines.append(f"{key}={current[key]}")

    env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    os.environ["SHOPIFY_ACCESS_TOKEN"] = access_token
    if shop:
        os.environ["SHOPIFY_SHOP"] = _normalized_shop(shop)
    if scopes:
        os.environ["SHOPIFY_APP_SCOPES"] = scopes

    try:
        from shopify_integration.models import ShopifyToken
        normalized = _normalized_shop(shop)
        ShopifyToken.objects.update_or_create(
            shop=normalized,
            defaults={"access_token": access_token, "scopes": scopes or ""},
        )
    except Exception:
        pass
