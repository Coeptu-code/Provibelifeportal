import os
from pathlib import Path
from uuid import uuid4

from supabase import create_client


PRODUCT_IMAGE_BUCKET = "product-info"


def _build_product_image_path(filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".bin"
    return f"products/{uuid4().hex}{ext}"


def upload_product_image(file_obj) -> str:
    project_url = os.getenv("SUPABASE_PROJECT_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not project_url or not service_role_key:
        raise ValueError(
            "Supabase storage is not configured. "
            "Set SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY."
        )

    file_path = _build_product_image_path(getattr(file_obj, "name", "upload.bin"))
    file_obj.seek(0)
    content = file_obj.read()

    supabase = create_client(project_url, service_role_key)
    supabase.storage.from_(PRODUCT_IMAGE_BUCKET).upload(
        file_path,
        content,
        {"content-type": getattr(file_obj, "content_type", "application/octet-stream")},
    )

    public_url_response = supabase.storage.from_(PRODUCT_IMAGE_BUCKET).get_public_url(file_path)
    if isinstance(public_url_response, dict):
        return public_url_response.get("publicUrl", "")
    return public_url_response
