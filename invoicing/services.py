from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from customers.models import PaymentTerms
from fulfillment.shipping_quote import ShippingQuoteError, quote_shipping_for_order
from invoicing.models import Invoice, InvoiceStatus, ShippingQuoteStatus
from invoicing.pdf import render_invoice_pdf
from orders.models import OrderStatus
from shopify_integration.client import ShopifyError
from shopify_integration.services import ShopifySyncError, send_invoice_to_shopify


def _days_until_due(payment_terms):
    if payment_terms == PaymentTerms.NET_15:
        return 15
    if payment_terms == PaymentTerms.NET_30:
        return 30
    return 0


def _build_invoice_number(order_id):
    return f"INV-{timezone.now():%Y%m%d}-{order_id:06d}"


def _default_currency():
    return (getattr(settings, "SHOPIFY_DEFAULT_CURRENCY", "") or settings.STRIPE_CURRENCY or "usd").lower()


@transaction.atomic
def create_invoice_for_order(
    order,
    shipping_total=Decimal("0"),
    tax_total=Decimal("0"),
    shipping_quote=None,
    shipping_input_source=Invoice.ShippingInputSource.FALLBACK_ZERO,
):
    if order.status not in {OrderStatus.APPROVED, OrderStatus.SHIPPED, OrderStatus.PARTIALLY_SHIPPED}:
        raise ValueError("Invoice can only be generated for approved, shipped, or partially shipped orders.")

    shipping_total = Decimal(shipping_total or "0").quantize(Decimal("0.01"))
    tax_total = Decimal(tax_total or "0").quantize(Decimal("0.01"))
    subtotal = order.subtotal
    total = subtotal + shipping_total + tax_total
    due_date = timezone.localdate() + timedelta(days=_days_until_due(order.customer.payment_terms))

    invoice, _ = Invoice.objects.update_or_create(
        order=order,
        invoice_kind=Invoice.InvoiceKind.PRIMARY,
        defaults={
            "customer": order.customer,
            "invoice_number": _build_invoice_number(order.id),
            "subtotal": subtotal,
            "shipping_total": shipping_total,
            "tax_total": tax_total,
            "total": total,
            "status": InvoiceStatus.DRAFT,
            "due_date": due_date,
            "shipping_currency": getattr(shipping_quote, "currency", _default_currency()),
            "shipping_carrier": getattr(shipping_quote, "carrier", ""),
            "shipping_service": getattr(shipping_quote, "service", ""),
            "shipping_rate_id": getattr(shipping_quote, "rate_id", ""),
            "shipping_quoted_at": timezone.now() if shipping_quote else None,
            "shipping_quote_status": ShippingQuoteStatus.SUCCESS if shipping_quote else ShippingQuoteStatus.NOT_QUOTED,
            "shipping_quote_reason": "",
            "shipping_input_source": shipping_input_source,
        },
    )
    render_invoice_pdf(invoice)
    return invoice


@transaction.atomic
def mark_invoice_quote_failed(order, reason: str):
    subtotal = order.subtotal
    due_date = timezone.localdate() + timedelta(days=_days_until_due(order.customer.payment_terms))
    invoice, _ = Invoice.objects.update_or_create(
        order=order,
        invoice_kind=Invoice.InvoiceKind.PRIMARY,
        defaults={
            "customer": order.customer,
            "invoice_number": _build_invoice_number(order.id),
            "subtotal": subtotal,
            "shipping_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "total": subtotal,
            "status": InvoiceStatus.DRAFT,
            "due_date": due_date,
            "shipping_quote_status": ShippingQuoteStatus.FAILED,
            "shipping_quote_reason": reason[:1000],
            "shipping_quoted_at": timezone.now(),
            "shipping_input_source": Invoice.ShippingInputSource.FALLBACK_ZERO,
        },
    )
    render_invoice_pdf(invoice)
    return invoice


@transaction.atomic
def send_invoice_to_provider(invoice: Invoice):
    if getattr(settings, "SHOPIFY_ENABLED", False):
        try:
            return send_invoice_to_shopify(invoice)
        except (ShopifyError, ShopifySyncError) as exc:
            invoice.shipping_quote_reason = str(exc)[:1000]
            invoice.save(update_fields=["shipping_quote_reason"])
            raise

    if not getattr(settings, "STRIPE_INVOICING_ENABLED", True):
        return invoice
    return invoice


def _shipping_enabled():
    provider = str(getattr(settings, "SHIPPING_PROVIDER", "none")).lower()
    if provider in {"shopify", "easypost"}:
        return True
    return bool(getattr(settings, "EASYPOST_ENABLED", False) and settings.EASYPOST_API_KEY)


def get_approval_shipping_estimate(order):
    if _shipping_enabled():
        try:
            quote = quote_shipping_for_order(order)
            return {
                "amount": Decimal(str(quote.amount)).quantize(Decimal("0.01")),
                "quote": quote,
                "source": Invoice.ShippingInputSource.ESTIMATED_API,
                "reason": "",
            }
        except ShippingQuoteError as exc:
            return {
                "amount": Decimal("0.00"),
                "quote": None,
                "source": Invoice.ShippingInputSource.FALLBACK_ZERO,
                "reason": str(exc),
            }
    return {
        "amount": Decimal("0.00"),
        "quote": None,
        "source": Invoice.ShippingInputSource.FALLBACK_ZERO,
        "reason": "Shipping provider disabled.",
    }


@transaction.atomic
def create_and_send_primary_invoice(order, shipping_override=None):
    estimate = get_approval_shipping_estimate(order)
    quote = estimate["quote"]
    source = estimate["source"]
    shipping_total = estimate["amount"]
    if shipping_override is not None:
        shipping_total = Decimal(shipping_override).quantize(Decimal("0.01"))
        source = Invoice.ShippingInputSource.MANUAL_OVERRIDE
        quote = None

    invoice = create_invoice_for_order(
        order=order,
        shipping_total=shipping_total,
        tax_total=Decimal("0.00"),
        shipping_quote=quote,
        shipping_input_source=source,
    )
    if estimate["reason"] and source != Invoice.ShippingInputSource.MANUAL_OVERRIDE:
        invoice.shipping_quote_reason = estimate["reason"][:1000]
        invoice.save(update_fields=["shipping_quote_reason"])
    send_invoice_to_provider(invoice)
    return invoice


def _build_adjustment_number(parent_invoice_id, kind):
    suffix = "D" if kind == Invoice.InvoiceKind.ADJUSTMENT_DEBIT else "C"
    return f"INV-ADJ-{parent_invoice_id:06d}-{suffix}-{timezone.now():%H%M%S}"


@transaction.atomic
def create_shipping_adjustment_invoice(order, parent_invoice, delta_amount):
    delta_amount = Decimal(delta_amount).quantize(Decimal("0.01"))
    if delta_amount == Decimal("0.00"):
        return None

    kind = (
        Invoice.InvoiceKind.ADJUSTMENT_DEBIT
        if delta_amount > 0
        else Invoice.InvoiceKind.ADJUSTMENT_CREDIT
    )
    due_date = timezone.localdate() + timedelta(days=_days_until_due(order.customer.payment_terms))
    invoice = Invoice.objects.create(
        order=order,
        parent_invoice=parent_invoice,
        customer=order.customer,
        invoice_number=_build_adjustment_number(parent_invoice.id, kind),
        invoice_kind=kind,
        subtotal=delta_amount,
        shipping_total=Decimal("0.00"),
        tax_total=Decimal("0.00"),
        total=delta_amount,
        status=InvoiceStatus.DRAFT,
        due_date=due_date,
        shipping_currency=parent_invoice.shipping_currency or _default_currency(),
        shipping_quote_status=ShippingQuoteStatus.NOT_QUOTED,
        shipping_input_source=Invoice.ShippingInputSource.ESTIMATED_API,
    )
    render_invoice_pdf(invoice)
    send_invoice_to_provider(invoice)
    return invoice


@transaction.atomic
def reconcile_shipping_after_ship(order, actual_shipping_quote=None):
    primary = (
        Invoice.objects.filter(order=order, invoice_kind=Invoice.InvoiceKind.PRIMARY)
        .order_by("-created_at")
        .first()
    )
    if not primary:
        return None

    if actual_shipping_quote is not None:
        actual_shipping = Decimal(str(actual_shipping_quote.amount)).quantize(Decimal("0.01"))
    elif _shipping_enabled():
        try:
            quote = quote_shipping_for_order(order)
            actual_shipping = Decimal(str(quote.amount)).quantize(Decimal("0.01"))
        except ShippingQuoteError:
            return None
    else:
        actual_shipping = primary.shipping_total

    delta = (actual_shipping - primary.shipping_total).quantize(Decimal("0.01"))
    if delta == Decimal("0.00"):
        return None
    return create_shipping_adjustment_invoice(order, primary, delta)
