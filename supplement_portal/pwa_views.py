from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse
from django.views.static import serve


PUBLIC_DIR = Path(settings.BASE_DIR) / "public"


def _serve_public_file(path: Path, content_type: str):
    if not path.exists() or not path.is_file():
        return HttpResponseNotFound("Not found")
    response = FileResponse(path.open("rb"), content_type=content_type)
    return response


def manifest(request):
    return _serve_public_file(
        PUBLIC_DIR / "manifest.json",
        "application/manifest+json",
    )


def service_worker(request):
    response = _serve_public_file(
        PUBLIC_DIR / "sw.js",
        "application/javascript",
    )
    response["Service-Worker-Allowed"] = "/"
    return response


def pvl_static(request, path):
    # Serve icon pack at /PVL/... so manifest + iOS icon URLs remain root-based.
    return serve(request, path, document_root=PUBLIC_DIR / "PVL")


def hooks_static(request, path):
    return serve(request, path, document_root=Path(settings.BASE_DIR) / "hooks")


def components_static(request, path):
    return serve(request, path, document_root=Path(settings.BASE_DIR) / "components")


def retailer_mobile_entry(request):
    if request.user.is_authenticated:
        if getattr(request.user, "is_customer_user", False):
            return redirect("customers:dashboard")
        if (
            getattr(request.user, "is_ops_user", False)
            or getattr(request.user, "is_staff", False)
            or getattr(request.user, "is_superuser", False)
        ):
            return redirect("admin_portal:dashboard")

    login_url = reverse("login")
    return redirect(f"{login_url}?next={reverse('root_redirect')}")
