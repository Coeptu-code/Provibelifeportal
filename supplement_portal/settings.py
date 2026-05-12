import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-local-dev-key")
DEBUG = True  # TEMPORARY - for debugging 500 error
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")



INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "customers",
    "products",
    "pricing",
    "orders",
    "fulfillment",
    "invoicing",
    "payments",
    "warehouse",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "supplement_portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "supplement_portal.wsgi.application"


DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Chicago")

USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / "public"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or "test" in sys.argv
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "root_redirect"
LOGOUT_REDIRECT_URL = "login"

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "usd")
STRIPE_INVOICING_ENABLED = env_bool("STRIPE_INVOICING_ENABLED", True)
EASYPOST_API_KEY = os.getenv("EASYPOST_API_KEY", "")
EASYPOST_ENABLED = env_bool("EASYPOST_ENABLED", False)
SHIPPING_PROVIDER = os.getenv("SHIPPING_PROVIDER", "none")

SHIP_FROM_NAME = os.getenv("SHIP_FROM_NAME", "")
SHIP_FROM_STREET1 = os.getenv("SHIP_FROM_STREET1", "")
SHIP_FROM_CITY = os.getenv("SHIP_FROM_CITY", "")
SHIP_FROM_STATE = os.getenv("SHIP_FROM_STATE", "")
SHIP_FROM_ZIP = os.getenv("SHIP_FROM_ZIP", "")
SHIP_FROM_COUNTRY = os.getenv("SHIP_FROM_COUNTRY", "US")
SHIP_FROM_PHONE = os.getenv("SHIP_FROM_PHONE", "")

SHOPIFY_ENABLED = env_bool("SHOPIFY_ENABLED", False)
SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", os.getenv("SHOPIFY_SHOP_DOMAIN", "")).strip()
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", os.getenv("SHOPIFY_API_KEY", "")).strip()
SHOPIFY_CLIENT_SECRET = os.getenv(
    "SHOPIFY_CLIENT_SECRET", os.getenv("SHOPIFY_API_SECRET", "")
).strip()
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04").strip()
SHOPIFY_REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI", "").strip()
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "").strip()
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "").strip()
SHOPIFY_APP_SCOPES = env_list("SHOPIFY_APP_SCOPES", "")
SHOPIFY_APP_URL = os.getenv("SHOPIFY_APP_URL", "").strip()
SHOPIFY_CARRIER_SERVICE_ENABLED = env_bool("SHOPIFY_CARRIER_SERVICE_ENABLED", True)
SHOPIFY_CARRIER_SERVICE_NAME = os.getenv(
    "SHOPIFY_CARRIER_SERVICE_NAME", "Pro Vibe Live Rates"
).strip()
SHOPIFY_CARRIER_CALLBACK_URL = os.getenv("SHOPIFY_CARRIER_CALLBACK_URL", "").strip()
SHOPIFY_READ_ALL_ORDERS = env_bool("SHOPIFY_READ_ALL_ORDERS", False)
SHOPIFY_DEFAULT_CURRENCY = os.getenv("SHOPIFY_DEFAULT_CURRENCY", STRIPE_CURRENCY or "usd").strip()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@provibelife.com")
RESEND_ENABLED = env_bool("RESEND_ENABLED", False)
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

if not DEBUG:
    if SECRET_KEY == "django-insecure-local-dev-key":
        raise ValueError("DJANGO_SECRET_KEY must be set in production.")
    if not ALLOWED_HOSTS:
        raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production.")

    secure_proxy_header = os.getenv(
        "DJANGO_SECURE_PROXY_SSL_HEADER", "HTTP_X_FORWARDED_PROTO,https"
    )
    proxy_parts = [part.strip() for part in secure_proxy_header.split(",", 1) if part.strip()]
    if len(proxy_parts) == 2:
        SECURE_PROXY_SSL_HEADER = (proxy_parts[0], proxy_parts[1])
    else:
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", True)
    CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", True)
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False
    )
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
