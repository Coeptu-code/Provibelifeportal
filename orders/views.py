from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from accounts.activity import log_activity
from accounts.decorators import customer_required, ops_required, sales_required, warehouse_required
from customers.models import ShippingAddress
from fulfillment.shipping_quote import (
    ShippingQuoteError,
    quote_shipping_for_order,
    shipping_quote_provider_enabled,
)
from fulfillment.models import Shipment, ShipmentStatus
from invoicing.services import (
    create_and_send_primary_invoice,
    get_approval_shipping_estimate,
    reconcile_shipping_after_ship,
)
from orders.forms import CustomerOrderForm
from orders.models import Order, OrderItem, OrderStatus
from pricing.models import CustomerProduct
from pricing.services import get_active_customer_price
from products.models import Product
from shopify_integration.services import ShopifySyncError, sync_shipment_to_shopify
from orders.services import (
    ADMIN_ACTION_TO_STATUS,
    get_available_admin_actions,
    submit_order,
    transition_order_status,
    validate_order_item,
)


ORDER_DRAFT_SESSION_KEY = "customer_order_drafts"
ORDER_DRAFT_TTL_SECONDS = 15 * 60


class _QuoteItemProxy:
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity


class _QuoteItemsProxy:
    def __init__(self, items):
        self._items = items

    def select_related(self, *_args, **_kwargs):
        return self._items


class _QuoteOrderProxy:
    def __init__(self, customer, shipping_address, items):
        self.customer = customer
        self.shipping_address = shipping_address
        self.items = _QuoteItemsProxy(items)


class _DisabledShippingQuote:
    amount = Decimal("0.00")
    currency = "usd"
    carrier = "N/A"
    service = "Disabled"
    rate_id = ""
    raw_ref = ""


def _customer_order_items(customer):
    products = (
        CustomerProduct.objects.filter(customer=customer, active=True, product__active=True)
        .select_related("product")
        .order_by("product__sku")
    )
    items = []
    for cp in products:
        product = cp.product
        try:
            price = get_active_customer_price(customer, product)
            items.append(
                {
                    "product": product,
                    "unit_price": price.unit_price,
                    "minimum_quantity": price.minimum_quantity,
                    "available": True,
                    "reason": "",
                }
            )
        except ValidationError:
            items.append(
                {
                    "product": product,
                    "unit_price": None,
                    "minimum_quantity": None,
                    "available": False,
                    "reason": "No active negotiated price.",
                }
            )
    return items


def _apply_quantities(order_items, quantities=None):
    quantities = quantities or {}
    for row in order_items:
        key = f"quantity_{row['product'].id}"
        row["quantity"] = quantities.get(key, 1)


def _store_order_draft(request, payload):
    token = uuid4().hex
    drafts = request.session.get(ORDER_DRAFT_SESSION_KEY, {})
    drafts[token] = payload
    request.session[ORDER_DRAFT_SESSION_KEY] = drafts
    request.session.modified = True
    return token


def _replace_order_draft(request, token, payload):
    drafts = request.session.get(ORDER_DRAFT_SESSION_KEY, {})
    drafts[token] = payload
    request.session[ORDER_DRAFT_SESSION_KEY] = drafts
    request.session.modified = True


def _pop_order_draft(request, token):
    drafts = request.session.get(ORDER_DRAFT_SESSION_KEY, {})
    payload = drafts.pop(token, None)
    request.session[ORDER_DRAFT_SESSION_KEY] = drafts
    request.session.modified = True
    return payload


def _load_order_draft(request, token):
    drafts = request.session.get(ORDER_DRAFT_SESSION_KEY, {})
    payload = drafts.get(token)
    if not payload:
        return None

    created_at = parse_datetime(payload.get("created_at", ""))
    if not created_at:
        return None
    if timezone.is_naive(created_at):
        created_at = timezone.make_aware(created_at, timezone.get_current_timezone())

    if (timezone.now() - created_at).total_seconds() > ORDER_DRAFT_TTL_SECONDS:
        drafts.pop(token, None)
        request.session[ORDER_DRAFT_SESSION_KEY] = drafts
        request.session.modified = True
        return None
    return payload


def _quote_shipping_preview(customer, shipping_address, product, quantity):
    if not shipping_quote_provider_enabled():
        quote = _DisabledShippingQuote()
        quote.currency = (settings.SHOPIFY_DEFAULT_CURRENCY or settings.STRIPE_CURRENCY or "usd").lower()
        return quote
    proxy_order = _QuoteOrderProxy(
        customer=customer,
        shipping_address=shipping_address,
        items=[_QuoteItemProxy(product=product, quantity=quantity)],
    )
    return quote_shipping_for_order(proxy_order)


def _quote_changed(old_quote, new_quote):
    return any(
        [
            Decimal(str(old_quote.get("amount", "0"))) != new_quote.amount,
            str(old_quote.get("currency", "")).lower() != str(new_quote.currency).lower(),
            str(old_quote.get("carrier", "")) != str(new_quote.carrier),
            str(old_quote.get("service", "")) != str(new_quote.service),
        ]
    )


def _verification_context(
    customer, payload, product, unit_price, shipping_quote, draft_token, shipping_address, warning=None
):
    quantity = int(payload["quantity"])
    subtotal = (unit_price * quantity).quantize(Decimal("0.01"))
    shipping = Decimal(str(shipping_quote.amount)).quantize(Decimal("0.01"))
    total = (subtotal + shipping).quantize(Decimal("0.01"))
    requested_ship_date = parse_date(payload.get("requested_ship_date", "") or "")

    return {
        "draft_token": draft_token,
        "customer": customer,
        "product": product,
        "quantity": quantity,
        "unit_price": unit_price,
        "subtotal": subtotal,
        "shipping_total": shipping,
        "tax_total": Decimal("0.00"),
        "estimated_total": total,
        "po_number": payload.get("po_number", ""),
        "requested_ship_date": requested_ship_date,
        "shipping_address": shipping_address,
        "shipping_quote": shipping_quote,
        "quote_warning": warning,
    }


@customer_required
def order_new(request):
    customer = request.user.customer
    order_items = _customer_order_items(customer)
    quantities = {f"quantity_{row['product'].id}": 1 for row in order_items}
    _apply_quantities(order_items, quantities)

    if request.method == "POST":
        action = request.POST.get("action", "verify")

        if action == "confirm":
            draft_token = request.POST.get("draft_token", "").strip()
            payload = _load_order_draft(request, draft_token)
            if not payload or payload.get("customer_id") != customer.id:
                messages.error(request, "Your order verification expired. Please start again.")
                form = CustomerOrderForm(customer=customer)
                return render(
                    request,
                    "customer/order_new.html",
                    {"form": form, "order_items": order_items, "quantities": quantities},
                )

            try:
                product = Product.objects.get(id=payload["product_id"], active=True)
                shipping_address = customer.shipping_addresses.get(
                    id=payload["shipping_address_id"], is_active=True
                )
                quantity = int(payload["quantity"])
                unit_price = validate_order_item(customer, product, quantity)
                shipping_quote = _quote_shipping_preview(
                    customer, shipping_address, product, quantity
                )
            except (Product.DoesNotExist, ValueError, ValidationError) as exc:
                messages.error(request, str(exc))
                form = CustomerOrderForm(customer=customer)
                return render(
                    request,
                    "customer/order_new.html",
                    {"form": form, "order_items": order_items, "quantities": quantities},
                )
            except ShippingAddress.DoesNotExist:
                messages.error(request, "Shipping address is invalid or inactive.")
                form = CustomerOrderForm(customer=customer)
                return render(
                    request,
                    "customer/order_new.html",
                    {"form": form, "order_items": order_items, "quantities": quantities},
                )
            except ShippingQuoteError as exc:
                messages.error(request, f"Shipping quote failed: {exc}")
                form = CustomerOrderForm(customer=customer)
                return render(
                    request,
                    "customer/order_new.html",
                    {"form": form, "order_items": order_items, "quantities": quantities},
                )

            old_quote = payload.get("quote", {})
            if _quote_changed(old_quote, shipping_quote):
                payload["quote"] = {
                    "amount": str(shipping_quote.amount),
                    "currency": str(shipping_quote.currency),
                    "carrier": str(shipping_quote.carrier),
                    "service": str(shipping_quote.service),
                    "rate_id": str(shipping_quote.rate_id),
                    "raw_ref": str(shipping_quote.raw_ref),
                }
                payload["created_at"] = timezone.now().isoformat()
                _replace_order_draft(request, draft_token, payload)
                context = _verification_context(
                    customer,
                    payload,
                    product,
                    unit_price,
                    shipping_quote,
                    draft_token,
                    shipping_address,
                    warning=(
                        "Shipping quote changed. Review updated totals and submit again."
                        if shipping_quote_provider_enabled()
                        else None
                    ),
                )
                return render(request, "customer/order_review.html", context)

            requested_ship_date = parse_date(payload.get("requested_ship_date", "") or "")
            with transaction.atomic():
                order = Order.objects.create(
                    customer=customer,
                    po_number=payload.get("po_number", ""),
                    shipping_address=shipping_address,
                    requested_ship_date=requested_ship_date,
                    status=OrderStatus.DRAFT,
                )
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    extended_price=unit_price * quantity,
                )
                submit_order(order)
            _pop_order_draft(request, draft_token)
            messages.success(request, "Order submitted.")
            log_activity(request.user, "order_submitted", f"Order #{order.pk}", request)
            return redirect("customers:order_detail", pk=order.pk)

        form = CustomerOrderForm(request.POST, customer=customer)
        selected_product_id = request.POST.get("product_id", "").strip()

        for key in list(quantities.keys()):
            quantities[key] = request.POST.get(key, "1")
        _apply_quantities(order_items, quantities)

        if form.is_valid():
            if not selected_product_id:
                form.add_error(None, "Select an item and click Submit Order on that item card.")
            else:
                try:
                    product = Product.objects.get(id=int(selected_product_id), active=True)
                except (Product.DoesNotExist, ValueError):
                    form.add_error(None, "Selected product is invalid.")
                else:
                    if not CustomerProduct.objects.filter(
                        customer=customer, product=product, active=True
                    ).exists():
                        form.add_error(None, f"Customer is not approved to order SKU {product.sku}.")
                        return render(
                            request,
                            "customer/order_new.html",
                            {"form": form, "order_items": order_items, "quantities": quantities},
                        )

                    qty_key = f"quantity_{product.id}"
                    qty_raw = request.POST.get(qty_key, "1")
                    try:
                        quantity = int(qty_raw)
                    except ValueError:
                        form.add_error(None, "Quantity must be a whole number.")
                        quantity = None

                    if quantity is not None:
                        try:
                            unit_price = validate_order_item(customer, product, quantity)
                            shipping_quote = _quote_shipping_preview(
                                customer,
                                form.cleaned_data["shipping_address"],
                                product,
                                quantity,
                            )
                        except ValidationError as exc:
                            form.add_error(None, str(exc))
                        except ShippingQuoteError as exc:
                            form.add_error(None, f"Shipping quote failed: {exc}")
                        else:
                            payload = {
                                "customer_id": customer.id,
                                "product_id": product.id,
                                "quantity": quantity,
                                "po_number": form.cleaned_data["po_number"],
                                "requested_ship_date": (
                                    form.cleaned_data["requested_ship_date"].isoformat()
                                    if form.cleaned_data["requested_ship_date"]
                                    else ""
                                ),
                                "shipping_address_id": form.cleaned_data["shipping_address"].id,
                                "quote": {
                                    "amount": str(shipping_quote.amount),
                                    "currency": str(shipping_quote.currency),
                                    "carrier": str(shipping_quote.carrier),
                                    "service": str(shipping_quote.service),
                                    "rate_id": str(shipping_quote.rate_id),
                                    "raw_ref": str(shipping_quote.raw_ref),
                                },
                                "created_at": timezone.now().isoformat(),
                            }
                            draft_token = _store_order_draft(request, payload)
                            context = _verification_context(
                                customer,
                                payload,
                                product,
                                unit_price,
                                shipping_quote,
                                draft_token,
                                form.cleaned_data["shipping_address"],
                                warning=(
                                    "Shipping quote is currently disabled. Shipping is shown as $0.00."
                                    if not shipping_quote_provider_enabled()
                                    else None
                                ),
                            )
                            return render(request, "customer/order_review.html", context)
    else:
        form = CustomerOrderForm(customer=customer)
    return render(
        request,
        "customer/order_new.html",
        {"form": form, "order_items": order_items, "quantities": quantities},
    )


@customer_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user.customer).order_by("-created_at")
    return render(request, "customer/order_history.html", {"orders": orders})


@customer_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("shipping_address"), pk=pk, customer=request.user.customer
    )
    return render(request, "customer/order_detail.html", {"order": order})


@customer_required
def order_review(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user.customer)
    shipping_total = Decimal("0.00")
    subtotal = order.subtotal
    return render(
        request,
        "customer/order_review.html",
        {
            "order": order,
            "subtotal": subtotal,
            "shipping_total": shipping_total,
            "tax_total": Decimal("0.00"),
            "estimated_total": subtotal + shipping_total,
            "shipping_quote": None,
        },
    )


@ops_required
def admin_orders(request):
    show_archived = request.GET.get("archived", "").strip() in {"1", "true", "yes", "on"}
    orders = Order.objects.select_related("customer").order_by("-created_at")
    if not show_archived:
        orders = orders.filter(archived_at__isnull=True)

    if request.user.role in ("sales_rep", "sales_lead"):
        orders = orders.filter(customer__in=request.user.get_accessible_customers())

    return render(
        request,
        "admin_portal/orders.html",
        {"orders": orders, "show_archived": show_archived},
    )


@ops_required
def admin_order_detail(request, pk):
    queryset = Order.objects.select_related("customer", "shipping_address")
    if request.user.role in ("sales_rep", "sales_lead"):
        queryset = queryset.filter(customer__in=request.user.get_accessible_customers())
    order = get_object_or_404(queryset, pk=pk)
    estimate = get_approval_shipping_estimate(order)
    return render(
        request,
        "admin_portal/order_detail.html",
        {
            "order": order,
            "available_actions": get_available_admin_actions(order),
            "approval_shipping_estimate": estimate["amount"],
            "approval_shipping_reason": estimate["reason"],
        },
    )


@ops_required
def admin_order_archive(request, pk):
    if request.method != "POST":
        return redirect("admin_portal:order_detail", pk=pk)

    order = get_object_or_404(Order, pk=pk)
    if order.archived_at:
        order.archived_at = None
        order.save(update_fields=["archived_at", "updated_at"])
        messages.success(request, "Order unarchived.")
    else:
        order.archived_at = timezone.now()
        order.save(update_fields=["archived_at", "updated_at"])
        messages.success(request, "Order archived.")
    return redirect("admin_portal:orders")


def admin_order_action(request, pk):
    if request.method != "POST":
        return redirect("admin_portal:order_detail", pk=pk)

    queryset = Order.objects.all()
    if request.user.role in ("sales_rep", "sales_lead"):
        queryset = queryset.filter(customer__in=request.user.get_accessible_customers())
    order = get_object_or_404(queryset, pk=pk)

    action = request.POST.get("action")
    target_status = ADMIN_ACTION_TO_STATUS.get(action)
    if not target_status:
        messages.error(request, "Unknown action.")
        return redirect("admin_portal:order_detail", pk=pk)

    financial_actions = {OrderStatus.APPROVED}
    if target_status in financial_actions and request.user.role == "warehouse_staff":
        messages.error(request, "You do not have permission to approve orders.")
        return redirect("admin_portal:order_detail", pk=pk)

    try:
        transition_order_status(order, target_status)
        if target_status == OrderStatus.APPROVED:
            shipping_override_raw = request.POST.get("shipping_override", "").strip()
            shipping_override = None
            if shipping_override_raw:
                try:
                    shipping_override = Decimal(shipping_override_raw)
                    if shipping_override < 0:
                        raise ValueError
                except ValueError:
                    messages.error(request, "Shipping override must be a valid non-negative amount.")
                    return redirect("admin_portal:order_detail", pk=pk)

            invoice = create_and_send_primary_invoice(order, shipping_override=shipping_override)
            if shipping_override is not None:
                messages.success(
                    request,
                    f"Order moved to {target_status}. Invoice {invoice.invoice_number} sent with manual shipping ${invoice.shipping_total}.",
                )
            else:
                messages.success(
                    request,
                    f"Order moved to {target_status}. Invoice {invoice.invoice_number} sent automatically.",
                )
            log_activity(request.user, "order_action", f"Order #{pk} → {action}", request)
            return redirect("admin_portal:order_detail", pk=pk)

        if target_status in {OrderStatus.PARTIALLY_SHIPPED, OrderStatus.SHIPPED}:
            Shipment.objects.create(
                order=order,
                carrier=request.POST.get("carrier", ""),
                tracking_number=request.POST.get("tracking_number", ""),
                shipped_at=timezone.now(),
                status=ShipmentStatus.SHIPPED,
            )
            latest_shipment = order.shipments.order_by("-created_at").first()
            if latest_shipment:
                try:
                    sync_shipment_to_shopify(latest_shipment)
                except ShopifySyncError:
                    pass
            adjustment = reconcile_shipping_after_ship(order)
            if adjustment:
                messages.success(
                    request,
                    f"Order moved to {target_status}. Shipping adjustment invoice {adjustment.invoice_number} sent (${adjustment.total}).",
                )
            else:
                messages.success(request, f"Order moved to {target_status}.")
            log_activity(request.user, "order_action", f"Order #{pk} → {action}", request)
            return redirect("admin_portal:order_detail", pk=pk)
        messages.success(request, f"Order moved to {target_status}.")
        log_activity(request.user, "order_action", f"Order #{pk} → {action}", request)
    except (ValidationError, ValueError) as exc:
        messages.error(request, str(exc))
    return redirect("admin_portal:order_detail", pk=pk)

# Create your views here.
