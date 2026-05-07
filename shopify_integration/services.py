from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from customers.models import Customer
from fulfillment.models import Shipment
from invoicing.models import Invoice, InvoiceStatus
from orders.models import Order, OrderStatus
from payments.models import Payment, PaymentMethod, ShopifyWebhookEvent
from products.models import Product
from shopify_integration.client import ShopifyError, admin_graphql, admin_rest


class ShopifySyncError(Exception):
    pass


def _parse_numeric_id(raw_value: str | int | None) -> str:
    if raw_value is None:
        return ""
    value = str(raw_value)
    if "/" in value:
        value = value.rsplit("/", 1)[-1]
    return value


def _split_name(name: str) -> tuple[str, str]:
    parts = [part for part in (name or "").strip().split(" ") if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def customer_contact_email(customer: Customer) -> str:
    user = customer.users.exclude(email="").order_by("id").first()
    if not user:
        raise ShopifySyncError(f"Customer {customer.name} has no email for Shopify invoicing.")
    return user.email


def ensure_shopify_product_mapping(product: Product) -> str:
    if product.shopify_variant_id:
        return product.shopify_variant_id

    query = """
    query ProductVariantBySku($query: String!) {
      productVariants(first: 1, query: $query) {
        edges {
          node {
            id
            legacyResourceId
            sku
            product {
              id
              legacyResourceId
            }
          }
        }
      }
    }
    """
    result = admin_graphql(query, {"query": f"sku:{product.sku}"})
    edges = result.get("productVariants", {}).get("edges", [])
    if not edges:
        raise ShopifySyncError(f"SKU {product.sku} could not be resolved in Shopify.")

    node = edges[0]["node"]
    product.shopify_variant_id = _parse_numeric_id(node.get("legacyResourceId") or node.get("id"))
    product.shopify_product_id = _parse_numeric_id(
        node.get("product", {}).get("legacyResourceId") or node.get("product", {}).get("id")
    )
    product.save(update_fields=["shopify_variant_id", "shopify_product_id"])
    return product.shopify_variant_id


def ensure_shopify_customer(customer: Customer) -> str:
    if customer.shopify_customer_id:
        return customer.shopify_customer_id

    email = customer_contact_email(customer)
    query = """
    query CustomerByEmail($query: String!) {
      customers(first: 1, query: $query) {
        edges {
          node {
            id
            legacyResourceId
          }
        }
      }
    }
    """
    result = admin_graphql(query, {"query": f"email:{email}"})
    edges = result.get("customers", {}).get("edges", [])
    if edges:
        customer.shopify_customer_id = _parse_numeric_id(
            edges[0]["node"].get("legacyResourceId") or edges[0]["node"].get("id")
        )
        customer.save(update_fields=["shopify_customer_id"])
        return customer.shopify_customer_id

    first_name, last_name = _split_name(customer.name)
    created = admin_rest(
        "POST",
        "customers.json",
        payload={
            "customer": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "tags": "provibelifeportal",
            }
        },
    )
    shopify_customer = created.get("customer", {})
    customer.shopify_customer_id = _parse_numeric_id(shopify_customer.get("id"))
    customer.save(update_fields=["shopify_customer_id"])
    return customer.shopify_customer_id


def _note_attributes(invoice: Invoice) -> list[dict[str, str]]:
    attrs = [
        {"name": "local_invoice_id", "value": str(invoice.id)},
        {"name": "local_order_id", "value": str(invoice.order_id)},
        {"name": "invoice_kind", "value": invoice.invoice_kind},
    ]
    if invoice.parent_invoice_id:
        attrs.append({"name": "parent_invoice_id", "value": str(invoice.parent_invoice_id)})
    return attrs


def _shipping_line(invoice: Invoice) -> dict | None:
    if invoice.shipping_total <= 0:
        return None
    title = "Shipping"
    if invoice.shipping_carrier or invoice.shipping_service:
        title = f"Shipping ({invoice.shipping_carrier} {invoice.shipping_service})".strip()
    return {"title": title, "price": f"{invoice.shipping_total:.2f}"}


def _draft_order_payload(invoice: Invoice) -> dict:
    email = customer_contact_email(invoice.customer)
    customer_id = ensure_shopify_customer(invoice.customer)
    shipping_address = invoice.order.shipping_address

    if invoice.invoice_kind == Invoice.InvoiceKind.PRIMARY:
        line_items = []
        for item in invoice.order.items.select_related("product"):
            variant_id = ensure_shopify_product_mapping(item.product)
            line_items.append(
                {
                    "variant_id": int(variant_id),
                    "quantity": item.quantity,
                    "price": f"{item.unit_price:.2f}",
                }
            )
    else:
        title = "Shipping Adjustment"
        if invoice.invoice_kind == Invoice.InvoiceKind.ADJUSTMENT_CREDIT:
            title = "Shipping Credit Adjustment"
        line_items = [
            {
                "title": title,
                "quantity": 1,
                "price": f"{abs(invoice.total):.2f}",
                "taxable": False,
            }
        ]

    payload = {
        "draft_order": {
            "customer": {"id": int(customer_id)},
            "email": email,
            "use_customer_default_address": False,
            "line_items": line_items,
            "note": f"Portal invoice {invoice.invoice_number}",
            "note_attributes": _note_attributes(invoice),
            "tags": f"provibelifeportal,{invoice.invoice_kind.lower()}",
        }
    }
    shipping_line = _shipping_line(invoice)
    if shipping_line:
        payload["draft_order"]["shipping_line"] = shipping_line
    if shipping_address:
        payload["draft_order"]["shipping_address"] = {
            "name": invoice.customer.name,
            "address1": shipping_address.line1,
            "address2": shipping_address.line2,
            "city": shipping_address.city,
            "province": shipping_address.state,
            "zip": shipping_address.postal_code,
            "country_code": shipping_address.country,
        }
    return payload


@transaction.atomic
def send_invoice_to_shopify(invoice: Invoice) -> Invoice:
    if not invoice.shopify_draft_order_id:
        payload = _draft_order_payload(invoice)
        created = admin_rest("POST", "draft_orders.json", payload=payload)
        draft_order = created.get("draft_order", {})
        invoice.shopify_draft_order_id = _parse_numeric_id(draft_order.get("id"))
        invoice.shopify_hosted_invoice_url = draft_order.get("invoice_url", "")
        invoice.shopify_order_id = _parse_numeric_id(draft_order.get("order_id"))

    email = customer_contact_email(invoice.customer)
    admin_rest(
        "POST",
        f"draft_orders/{invoice.shopify_draft_order_id}/send_invoice.json",
        payload={"draft_order_invoice": {"to": email}},
    )
    invoice.status = InvoiceStatus.SENT
    invoice.save(
        update_fields=[
            "shopify_draft_order_id",
            "shopify_hosted_invoice_url",
            "shopify_order_id",
            "status",
        ]
    )
    return invoice


@transaction.atomic
def sync_shipment_to_shopify(shipment: Shipment) -> Shipment:
    order_id = shipment.order.shopify_order_id
    if not order_id:
        invoice = shipment.order.invoices.filter(invoice_kind=Invoice.InvoiceKind.PRIMARY).first()
        if invoice and invoice.shopify_order_id:
            order_id = invoice.shopify_order_id
            shipment.order.shopify_order_id = order_id
            shipment.order.save(update_fields=["shopify_order_id"])

    if not order_id:
        raise ShopifySyncError("No Shopify order exists yet for this shipment.")

    result = admin_rest("GET", f"orders/{order_id}/fulfillment_orders.json")
    fulfillment_orders = result.get("fulfillment_orders", [])
    if not fulfillment_orders:
        raise ShopifySyncError("Shopify returned no fulfillment orders for this order.")

    selected = fulfillment_orders[0]
    response = admin_rest(
        "POST",
        "fulfillments.json",
        payload={
            "fulfillment": {
                "notify_customer": False,
                "tracking_info": {
                    "company": shipment.carrier,
                    "number": shipment.tracking_number,
                },
                "line_items_by_fulfillment_order": [
                    {"fulfillment_order_id": selected["id"]}
                ],
            }
        },
    )
    fulfillment = response.get("fulfillment", {})
    shipment.shopify_fulfillment_id = _parse_numeric_id(fulfillment.get("id"))
    shipment.shopify_fulfillment_order_id = _parse_numeric_id(selected.get("id"))
    shipment.save(update_fields=["shopify_fulfillment_id", "shopify_fulfillment_order_id"])
    return shipment


def _note_attributes_dict(payload: dict) -> dict[str, str]:
    attrs = {}
    for item in payload.get("note_attributes") or []:
        name = item.get("name")
        value = item.get("value")
        if name:
            attrs[str(name)] = str(value or "")
    return attrs


def _lookup_invoice(payload: dict) -> Invoice | None:
    attrs = _note_attributes_dict(payload)
    local_invoice_id = attrs.get("local_invoice_id")
    if local_invoice_id:
        invoice = Invoice.objects.filter(pk=local_invoice_id).first()
        if invoice:
            return invoice
    if payload.get("id"):
        return Invoice.objects.filter(shopify_order_id=str(payload["id"])).first()
    return None


def _lookup_order(payload: dict, invoice: Invoice | None) -> Order | None:
    attrs = _note_attributes_dict(payload)
    local_order_id = attrs.get("local_order_id")
    if local_order_id:
        order = Order.objects.filter(pk=local_order_id).first()
        if order:
            return order
    if invoice:
        return invoice.order
    if payload.get("id"):
        return Order.objects.filter(shopify_order_id=str(payload["id"])).first()
    return None


def _sync_ids_from_payload(invoice: Invoice | None, order: Order | None, payload: dict) -> None:
    order_id = _parse_numeric_id(payload.get("id"))
    order_name = payload.get("name", "")
    if order and order_id and order.shopify_order_id != order_id:
        order.shopify_order_id = order_id
        order.shopify_order_name = order_name
        order.save(update_fields=["shopify_order_id", "shopify_order_name"])
    if invoice:
        fields = []
        if order_id and invoice.shopify_order_id != order_id:
            invoice.shopify_order_id = order_id
            fields.append("shopify_order_id")
        if payload.get("invoice_url") and invoice.shopify_hosted_invoice_url != payload.get("invoice_url"):
            invoice.shopify_hosted_invoice_url = payload.get("invoice_url")
            fields.append("shopify_hosted_invoice_url")
        if fields:
            invoice.save(update_fields=fields)


@transaction.atomic
def process_shopify_webhook(topic: str, payload: dict, event_id: str, shop_domain: str = "") -> bool:
    receipt, created = ShopifyWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={"event_type": topic, "shop_domain": shop_domain},
    )
    if not created and receipt.processed_at:
        return False

    invoice = _lookup_invoice(payload)
    order = _lookup_order(payload, invoice)
    _sync_ids_from_payload(invoice, order, payload)

    if topic == "orders/paid" and invoice:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=["status", "paid_at"])
        paid_amount = Decimal(str(payload.get("current_total_price") or payload.get("total_price") or "0"))
        if paid_amount > 0:
            Payment.objects.get_or_create(
                invoice=invoice,
                shopify_payment_id=str(payload.get("id", "")),
                defaults={
                    "amount": paid_amount,
                    "method": PaymentMethod.SHOPIFY,
                    "reference_number": payload.get("name", str(payload.get("id", ""))),
                    "received_at": timezone.now(),
                },
            )
    elif topic == "orders/cancelled":
        if invoice:
            invoice.status = InvoiceStatus.VOID
            invoice.save(update_fields=["status"])
        if order:
            order.status = OrderStatus.CANCELLED
            order.save(update_fields=["status", "updated_at"])
    elif topic == "orders/fulfilled" and order:
        order.status = OrderStatus.SHIPPED
        order.save(update_fields=["status", "updated_at"])
    elif topic == "orders/partially_fulfilled" and order:
        order.status = OrderStatus.PARTIALLY_SHIPPED
        order.save(update_fields=["status", "updated_at"])
    elif topic == "orders/updated" and invoice:
        financial_status = str(payload.get("financial_status", "")).lower()
        if financial_status == "paid":
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = invoice.paid_at or timezone.now()
        elif financial_status == "partially_paid":
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        elif financial_status in {"voided", "refunded"}:
            invoice.status = InvoiceStatus.VOID
        else:
            invoice.status = InvoiceStatus.OPEN if invoice.status != InvoiceStatus.PAID else invoice.status
        invoice.save(update_fields=["status", "paid_at"])

    receipt.processed_at = timezone.now()
    receipt.event_type = topic
    receipt.shop_domain = shop_domain
    receipt.save(update_fields=["event_type", "shop_domain", "processed_at"])
    return True
