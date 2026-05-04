from dataclasses import dataclass
from decimal import Decimal

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
                "weight": str(weight_oz.quantize(Decimal("0.01"))),
                "length": str(length_in.quantize(Decimal("0.01"))),
                "width": str(width_in.quantize(Decimal("0.01"))),
                "height": str(height_in.quantize(Decimal("0.01"))),
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


def quote_shipping_for_order(order) -> ShippingQuote:
    if not settings.EASYPOST_API_KEY:
        raise ShippingQuoteError("EASYPOST_API_KEY is not configured.")

    payload = {
        "shipment": {
            "to_address": _ship_to_address(order),
            "from_address": _ship_from_address(),
            "parcels": _build_parcels(order),
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
