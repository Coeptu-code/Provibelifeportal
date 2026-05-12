from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings


class ShippingQuoteError(Exception):
    pass


@dataclass
class ShippingQuote:
    amount: Decimal
    currency: str
    carrier: str
    service: str
    rate_id: str
    raw_ref: str


def _normalize_weight(weight: Decimal, unit: str) -> Decimal:
    if unit == "lb":
        return weight * Decimal("16")
    return weight


def _normalize_dimension(value: Decimal, unit: str) -> Decimal:
    if unit == "cm":
        return value / Decimal("2.54")
    return value


def _build_parcels(order):
    parcels = []
    for item in order.items.select_related("product"):
        product = item.product
        if (
            product.shipping_weight is None
            or product.shipping_length is None
            or product.shipping_width is None
            or product.shipping_height is None
        ):
            raise ShippingQuoteError(
                f"Product {product.sku} is missing shipping profile (weight/dimensions)."
            )

        weight_oz = _normalize_weight(Decimal(product.shipping_weight), product.shipping_weight_unit)
        length_in = _normalize_dimension(Decimal(product.shipping_length), product.shipping_dimension_unit)
        width_in = _normalize_dimension(Decimal(product.shipping_width), product.shipping_dimension_unit)
        height_in = _normalize_dimension(Decimal(product.shipping_height), product.shipping_dimension_unit)

        if min(weight_oz, length_in, width_in, height_in) <= 0:
            raise ShippingQuoteError(f"Product {product.sku} shipping profile values must be positive.")

        for _ in range(item.quantity):
            parcel = {
                "weight_oz": weight_oz.quantize(Decimal("0.01")),
                "length_in": length_in.quantize(Decimal("0.01")),
                "width_in": width_in.quantize(Decimal("0.01")),
                "height_in": height_in.quantize(Decimal("0.01")),
            }
            if product.shipping_package_type:
                parcel["predefined_package"] = product.shipping_package_type
            parcels.append(parcel)

    if not parcels:
        raise ShippingQuoteError("Order has no shippable items.")
    return parcels


def _ship_from_address():
    required = {
        "SHIP_FROM_NAME": settings.SHIP_FROM_NAME,
        "SHIP_FROM_STREET1": settings.SHIP_FROM_STREET1,
        "SHIP_FROM_CITY": settings.SHIP_FROM_CITY,
        "SHIP_FROM_STATE": settings.SHIP_FROM_STATE,
        "SHIP_FROM_ZIP": settings.SHIP_FROM_ZIP,
        "SHIP_FROM_COUNTRY": settings.SHIP_FROM_COUNTRY,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ShippingQuoteError(f"Missing ship-from settings: {', '.join(missing)}.")

    return {
        "name": settings.SHIP_FROM_NAME,
        "street1": settings.SHIP_FROM_STREET1,
        "city": settings.SHIP_FROM_CITY,
        "state": settings.SHIP_FROM_STATE,
        "zip": settings.SHIP_FROM_ZIP,
        "country": settings.SHIP_FROM_COUNTRY,
        "phone": settings.SHIP_FROM_PHONE or "",
    }


def _ship_to_address(order):
    ship_to = order.shipping_address
    if not ship_to:
        raise ShippingQuoteError("Order has no shipping address.")

    return {
        "name": order.customer.name,
        "street1": ship_to.line1,
        "street2": ship_to.line2,
        "city": ship_to.city,
        "state": ship_to.state,
        "zip": ship_to.postal_code,
        "country": ship_to.country,
    }


def _select_rate(rates, preferred_carrier: str):
    valid_rates = []
    for rate in rates:
        amount = rate.get("rate")
        if amount is None:
            continue
        try:
            decimal_amount = Decimal(str(amount))
        except Exception:
            continue
        valid_rates.append((decimal_amount, rate))

    if not valid_rates:
        raise ShippingQuoteError("No valid shipping rates returned by EasyPost.")

    preferred_carrier = (preferred_carrier or "").upper().strip()
    preferred = [
        (amount, rate)
        for amount, rate in valid_rates
        if str(rate.get("carrier", "")).upper() == preferred_carrier
    ]
    if preferred:
        preferred.sort(key=lambda x: x[0])
        return preferred[0][1]

    valid_rates.sort(key=lambda x: x[0])
    return valid_rates[0][1]


def _shipping_provider() -> str:
    provider = (getattr(settings, "SHIPPING_PROVIDER", "none") or "none").strip().lower()
    if provider in {"", "none"} and getattr(settings, "EASYPOST_ENABLED", False) and settings.EASYPOST_API_KEY:
        return "easypost"
    return provider


def shipping_quote_provider_enabled() -> bool:
    provider = _shipping_provider()
    if provider == "shopify":
        return bool(getattr(settings, "SHOPIFY_ENABLED", False))
    if provider == "easypost":
        return bool(getattr(settings, "EASYPOST_ENABLED", False) and settings.EASYPOST_API_KEY)
    return False


def _shopify_service_label(preferred_carrier: str) -> tuple[str, str]:
    carrier = (preferred_carrier or "").strip().upper() or "SHOPIFY"
    return carrier, "Portal Ground"


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _estimate_quote_from_weight(total_weight_oz: Decimal, parcel_count: int, preferred_carrier: str):
    carrier, service = _shopify_service_label(preferred_carrier)
    amount = Decimal("9.50")
    amount += total_weight_oz * Decimal("0.32")
    amount += Decimal(parcel_count) * Decimal("1.15")
    return ShippingQuote(
        amount=_quantize_money(amount),
        currency=(settings.SHOPIFY_DEFAULT_CURRENCY or "usd").lower(),
        carrier=carrier,
        service=service,
        rate_id=f"shopify-rate-{carrier.lower()}-{parcel_count}",
        raw_ref=f"shopify-estimate-{total_weight_oz.quantize(Decimal('0.01'))}",
    )


def _quote_via_shopify(order) -> ShippingQuote:
    _ship_to_address(order)
    parcels = _build_parcels(order)
    total_weight = sum((parcel["weight_oz"] for parcel in parcels), Decimal("0.00"))
    return _estimate_quote_from_weight(total_weight, len(parcels), getattr(order.customer, "preferred_carrier", ""))


def _quote_via_easypost(order) -> ShippingQuote:
    if not settings.EASYPOST_API_KEY:
        raise ShippingQuoteError("EASYPOST_API_KEY is not configured.")

    payload = {
        "shipment": {
            "to_address": _ship_to_address(order),
            "from_address": _ship_from_address(),
            "parcels": [
                {
                    "weight": str(parcel["weight_oz"]),
                    "length": str(parcel["length_in"]),
                    "width": str(parcel["width_in"]),
                    "height": str(parcel["height_in"]),
                    **({"predefined_package": parcel["predefined_package"]} if parcel.get("predefined_package") else {}),
                }
                for parcel in _build_parcels(order)
            ],
        }
    }
    try:
        response = requests.post(
            "https://api.easypost.com/v2/shipments",
            auth=(settings.EASYPOST_API_KEY, ""),
            json=payload,
            timeout=25,
        )
    except requests.RequestException as exc:
        raise ShippingQuoteError(f"EasyPost request error: {exc}") from exc
    if response.status_code >= 400:
        raise ShippingQuoteError(f"EasyPost rate request failed: {response.text[:500]}")

    data = response.json()
    selected = _select_rate(data.get("rates", []), getattr(order.customer, "preferred_carrier", ""))
    return ShippingQuote(
        amount=Decimal(str(selected["rate"])),
        currency=str(selected.get("currency", "USD")).lower(),
        carrier=str(selected.get("carrier", "")),
        service=str(selected.get("service", "")),
        rate_id=str(selected.get("id", "")),
        raw_ref=str(data.get("id", "")),
    )


def quote_shipping_for_order(order) -> ShippingQuote:
    provider = _shipping_provider()
    if provider == "shopify":
        return _quote_via_shopify(order)
    if provider == "easypost":
        return _quote_via_easypost(order)
    raise ShippingQuoteError("Shipping provider is disabled.")


def build_shopify_carrier_rates(payload: dict) -> list[dict]:
    rate_request = payload.get("rate", {})
    items = rate_request.get("items") or []
    if not items:
        return []

    total_weight_oz = Decimal("0.00")
    parcel_count = 0
    for item in items:
        quantity = int(item.get("quantity") or 1)
        grams = Decimal(str(item.get("grams") or "0"))
        if grams > 0:
            total_weight_oz += (grams / Decimal("28.349523125")) * quantity
        parcel_count += quantity

    destination = rate_request.get("destination", {})
    preferred_carrier = destination.get("province") or destination.get("country")
    quote = _estimate_quote_from_weight(total_weight_oz, max(parcel_count, 1), str(preferred_carrier))
    return [
        {
            "service_name": f"{quote.carrier} {quote.service}",
            "service_code": quote.rate_id,
            "total_price": str(int((quote.amount * 100).quantize(Decimal("1")))),
            "currency": quote.currency.upper(),
            "description": "Provibe portal live shipping estimate",
        }
    ]
