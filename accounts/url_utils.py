from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse


def _setting_value(key: str) -> str:
    return (getattr(settings, key, "") or "").strip()


def base_url(request=None) -> str:
    for candidate in (
        _setting_value("SITE_URL"),
        _setting_value("APP_URL"),
        _setting_value("SHOPIFY_APP_URL"),
    ):
        if candidate:
            return candidate.rstrip("/")

    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")

    return "http://localhost:8000"


def absolute_path(path: str, request=None, query: dict | None = None) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    if query:
        clean_path = f"{clean_path}?{urlencode(query)}"
    return f"{base_url(request=request)}{clean_path}"


def absolute_view_url(
    view_name: str,
    *,
    request=None,
    kwargs: dict | None = None,
    query: dict | None = None,
) -> str:
    return absolute_path(reverse(view_name, kwargs=kwargs), request=request, query=query)


def mobile_app_download_url(request=None) -> str:
    return absolute_path("/retailer-app/mobile", request=request)
