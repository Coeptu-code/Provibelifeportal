import csv
import io
import json
import os
import uuid

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from accounts.models import RetailerLead, RetailerMarketingPageToken
from accounts.url_utils import absolute_path


def _portal_mailer_api_key() -> str:
    return (os.getenv("PORTAL_MAILER_API_KEY", "") or "").strip()


def _authorized(request) -> bool:
    configured = _portal_mailer_api_key()
    if not configured:
        return False
    auth = (request.headers.get("Authorization", "") or "").strip()
    if auth.startswith("Bearer "):
        provided = auth.replace("Bearer ", "", 1).strip()
        return provided == configured
    return False


def _parse_payload(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


def _parse_leads_from_bulk_text(raw_text: str) -> list[dict]:
    text = (raw_text or "").strip()
    if not text:
        return []

    if text.startswith("[") or text.startswith("{"):
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("leads"), list):
            parsed = parsed["leads"]
        if not isinstance(parsed, list):
            raise ValueError("JSON must be a list or object with a leads list.")
        return [row for row in parsed if isinstance(row, dict)]

    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for row in reader:
        cleaned = {str(k or "").strip(): (v or "").strip() for k, v in row.items()}
        rows.append(cleaned)
    return rows


def _normalize_lead_input(raw: dict) -> dict:
    email = (raw.get("email") or raw.get("send_email") or raw.get("primary_contact_email") or "").strip().lower()
    if not email:
        raise ValueError("Lead email is required.")

    source = (raw.get("source") or raw.get("token_source") or "").strip()
    if source.startswith("<") and source.endswith(">"):
        source = source[1:-1].strip()

    is_test_raw = str(raw.get("is_test") or "").strip().lower()
    is_test = is_test_raw in {"1", "true", "yes", "y"}

    return {
        "email": email,
        "store_name": (raw.get("store_name") or raw.get("name") or raw.get("business_name") or "").strip(),
        "first_name": (raw.get("first_name") or "").strip(),
        "last_name": (raw.get("last_name") or "").strip(),
        "phone": (raw.get("phone") or "").strip(),
        "source": source,
        "is_test": is_test,
    }


def _token_url(request, token_obj: RetailerMarketingPageToken) -> str:
    return absolute_path(f"/pages/free-sample/{token_obj.token}/", request=request)


@csrf_exempt
@require_POST
def free_sample_tokens_bulk_create(request):
    if not _authorized(request):
        return JsonResponse({"detail": "Unauthorized."}, status=401)

    payload = _parse_payload(request)
    leads_payload = payload.get("leads")
    if leads_payload is None and payload.get("bulk_text"):
        try:
            leads_payload = _parse_leads_from_bulk_text(payload.get("bulk_text") or "")
        except Exception as exc:
            return JsonResponse({"detail": str(exc)}, status=400)

    if not isinstance(leads_payload, list) or not leads_payload:
        return JsonResponse({"detail": "leads list is required."}, status=400)

    source_prefix = (payload.get("source") or "").strip()
    created = []
    failures = []

    for index, row in enumerate(leads_payload):
        try:
            if not isinstance(row, dict):
                raise ValueError("Lead row must be an object.")
            normalized = _normalize_lead_input(row)
            source = normalized["source"] or source_prefix
            lead, _ = RetailerLead.objects.update_or_create(
                email=normalized["email"],
                defaults={
                    "store_name": normalized["store_name"],
                    "first_name": normalized["first_name"],
                    "last_name": normalized["last_name"],
                    "phone": normalized["phone"],
                },
            )
            token_obj = RetailerMarketingPageToken.objects.create(
                lead=lead,
                page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE,
                source=source,
                is_test=normalized["is_test"],
            )
            created.append(
                {
                    "index": index,
                    "email": lead.email,
                    "token": str(token_obj.token),
                    "free_sample_token": str(token_obj.token),
                    "free_sample_token_url": _token_url(request, token_obj),
                    "clicked": token_obj.click_count > 0,
                    "is_test": token_obj.is_test,
                    "source": token_obj.source,
                }
            )
        except Exception as exc:
            failures.append({"index": index, "error": str(exc), "row": row})

    return JsonResponse(
        {
            "created_count": len(created),
            "failed_count": len(failures),
            "tokens": created,
            "failures": failures,
        },
        status=200,
    )


@csrf_exempt
@require_GET
def free_sample_token_status(request, token):
    if not _authorized(request):
        return JsonResponse({"detail": "Unauthorized."}, status=401)

    token_raw = (token or "").strip()
    try:
        token_uuid = uuid.UUID(token_raw)
    except Exception:
        return JsonResponse({"detail": "Invalid token."}, status=400)

    token_obj = (
        RetailerMarketingPageToken.objects.select_related("lead")
        .filter(token=token_uuid, page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE)
        .first()
    )
    if not token_obj:
        return JsonResponse({"detail": "Token not found."}, status=404)

    return JsonResponse(
        {
            "token": str(token_obj.token),
            "email": token_obj.lead.email,
            "clicked": token_obj.click_count > 0,
            "click_count": token_obj.click_count,
            "first_clicked_at": token_obj.first_clicked_at,
            "last_clicked_at": token_obj.last_clicked_at,
            "is_test": token_obj.is_test,
            "source": token_obj.source,
            "expired": timezone.now() >= token_obj.expires_at,
            "expires_at": token_obj.expires_at,
            "free_sample_token_url": _token_url(request, token_obj),
        }
    )
