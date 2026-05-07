from django.urls import path

from payments.views import stripe_webhook
from shopify_integration.views import carrier_rate, oauth_callback, oauth_install, shopify_webhook

urlpatterns = [
    path("stripe/", stripe_webhook, name="stripe_webhook"),
    path("shopify/", shopify_webhook, name="shopify_webhook"),
    path("shopify/carrier-rate/", carrier_rate, name="shopify_carrier_rate"),
    path("auth/shopify/install/", oauth_install, name="shopify_oauth_install"),
    path("auth/shopify/callback/", oauth_callback, name="shopify_oauth_callback"),
]
