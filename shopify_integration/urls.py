from django.urls import path

from shopify_integration import views

app_name = "shopify_integration"

urlpatterns = [
    # Primary OAuth endpoints
    path("auth/shopify/install/", views.oauth_install, name="oauth_install"),
    path("auth/shopify/callback/", views.oauth_callback, name="oauth_callback"),
    # Backward-compatible aliases used in earlier setup notes
    path("webhooks/auth/shopify/install/", views.oauth_install, name="oauth_install_legacy"),
    path("webhooks/auth/shopify/callback/", views.oauth_callback, name="oauth_callback_legacy"),
    # Webhooks / carrier service callbacks
    path("webhooks/shopify/", views.shopify_webhook, name="shopify_webhook"),
    path("webhooks/shopify/carrier-rate/", views.carrier_rate, name="carrier_rate"),
]
