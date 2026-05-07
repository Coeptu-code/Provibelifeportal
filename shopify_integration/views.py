import json
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from fulfillment.shipping_quote import build_shopify_carrier_rates
from shopify_integration.client import (
    ShopifyError,
    build_oauth_install_url,
    exchange_code_for_token,
    persist_access_token,
    verify_oauth_hmac,
    verify_webhook_signature,
)
from shopify_integration.services import process_shopify_webhook


@require_GET
def oauth_install(request):
    if not settings.SHOPIFY_CLIENT_ID or not settings.SHOPIFY_CLIENT_SECRET:
        return HttpResponseBadRequest("Shopify OAuth is not configured.")

    state = uuid4().hex
    request.session["shopify_oauth_state"] = state
    install_url = build_oauth_install_url(state=state, shop=request.GET.get("shop"))
    return redirect(install_url)


@require_GET
def oauth_callback(request):
    params = {key: value for key, value in request.GET.items()}
    if not verify_oauth_hmac(params):
        return HttpResponseBadRequest("Invalid Shopify OAuth signature.")
    if params.get("state") != request.session.get("shopify_oauth_state"):
        return HttpResponseBadRequest("Invalid Shopify OAuth state.")
    code = params.get("code", "")
    shop = params.get("shop", "")
    if not code or not shop:
        return HttpResponseBadRequest("Missing Shopify OAuth parameters.")

    try:
        token_data = exchange_code_for_token(code=code, shop=shop)
        persist_access_token(
            access_token=token_data.get("access_token", ""),
            shop=shop,
            scopes=token_data.get("scope", ",".join(settings.SHOPIFY_APP_SCOPES)),
        )
    except ShopifyError as exc:
        return HttpResponseBadRequest(str(exc))

    if request.user.is_authenticated:
        messages.success(request, "Shopify OAuth completed and token persisted.")
        return redirect("root_redirect")
    return HttpResponse("Shopify OAuth completed.")


@csrf_exempt
@require_POST
def shopify_webhook(request):
    signature = request.META.get("HTTP_X_SHOPIFY_HMAC_SHA256", "")
    topic = request.META.get("HTTP_X_SHOPIFY_TOPIC", "")
    event_id = request.META.get("HTTP_X_SHOPIFY_EVENT_ID", "")
    shop_domain = request.META.get("HTTP_X_SHOPIFY_SHOP_DOMAIN", "")

    if not verify_webhook_signature(request.body, signature):
        return JsonResponse({"detail": "Invalid Shopify webhook signature."}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid Shopify webhook payload."}, status=400)

    process_shopify_webhook(topic=topic, payload=payload, event_id=event_id or uuid4().hex, shop_domain=shop_domain)
    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def carrier_rate(request):
    signature = request.META.get("HTTP_X_SHOPIFY_HMAC_SHA256", "")
    if settings.SHOPIFY_WEBHOOK_SECRET and not verify_webhook_signature(request.body, signature):
        return JsonResponse({"detail": "Invalid Shopify carrier signature."}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid carrier payload."}, status=400)

    return JsonResponse({"rates": build_shopify_carrier_rates(payload)})
