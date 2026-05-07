from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from accounts import views as account_views
from accounts.views import root_redirect, CustomPasswordResetConfirmView
from supplement_portal import pwa_views

urlpatterns = [
    path("manifest.json", pwa_views.manifest, name="pwa_manifest"),
    path("sw.js", pwa_views.service_worker, name="pwa_service_worker"),
    path("retailer-app/mobile", pwa_views.retailer_mobile_entry, name="retailer_mobile_entry"),
    path("retailer-app/mobile/", pwa_views.retailer_mobile_entry),
    path("shopify-test/", pwa_views.retailer_mobile_entry, name="shopify_test_home"),
    re_path(r"^PVL/(?P<path>.*)$", pwa_views.pvl_static, name="pvl_static"),
    re_path(r"^hooks/(?P<path>.*)$", pwa_views.hooks_static, name="hooks_static"),
    re_path(r"^components/(?P<path>.*)$", pwa_views.components_static, name="components_static"),
    path("", root_redirect, name="root_redirect"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/invite/<uuid:token>/", account_views.invitation_accept, name="invitation_accept"),
    path("accounts/password-reset/", account_views.custom_password_reset, name="password_reset"),
    path("accounts/password-reset/done/", TemplateView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("accounts/reset/done/", TemplateView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("retailer/create-account/", account_views.retailer_create_account, name="retailer_create_account"),
    path("", include("shopify_integration.urls")),
    path(
        "shopify-test/",
        include(("shopify_integration.urls", "shopify_integration_test"), namespace="shopify_integration_test"),
    ),
    path("customer/", include("customers.urls")),
    path("admin-portal/", include("supplement_portal.admin_portal_urls")),
    path("webhooks/", include("payments.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
