from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import TemplateView

from accounts import views as account_views
from accounts.views import root_redirect, CustomPasswordResetConfirmView

urlpatterns = [
    path("", root_redirect, name="root_redirect"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/invite/<uuid:token>/", account_views.invitation_accept, name="invitation_accept"),
    path("accounts/password-reset/", account_views.custom_password_reset, name="password_reset"),
    path("accounts/password-reset/done/", TemplateView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("accounts/reset/done/", TemplateView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("retailer/create-account/", account_views.retailer_create_account, name="retailer_create_account"),
    path("customer/", include("customers.urls")),
    path("admin-portal/", include("supplement_portal.admin_portal_urls")),
    path("webhooks/", include("payments.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
