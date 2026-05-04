from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from accounts.views import root_redirect

urlpatterns = [
    path("", root_redirect, name="root_redirect"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("customer/", include("customers.urls")),
    path("admin-portal/", include("supplement_portal.admin_portal_urls")),
    path("webhooks/", include("payments.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
