from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderItem, OrderStatus
from pricing.models import CustomerProduct
from pricing.services import get_active_customer_price

ALLOWED_ORDER_TRANSITIONS = {
    OrderStatus.DRAFT: {OrderStatus.SUBMITTED, OrderStatus.CANCELLED},
    OrderStatus.SUBMITTED: {OrderStatus.UNDER_REVIEW, OrderStatus.CANCELLED},
    OrderStatus.UNDER_REVIEW: {
        OrderStatus.APPROVED,
        OrderStatus.ON_HOLD,
        OrderStatus.CANCELLED,
    },
    OrderStatus.ON_HOLD: {OrderStatus.UNDER_REVIEW, OrderStatus.CANCELLED},
    OrderStatus.APPROVED: {OrderStatus.RELEASED_TO_WAREHOUSE, OrderStatus.CANCELLED},
    OrderStatus.RELEASED_TO_WAREHOUSE: {OrderStatus.PICKING, OrderStatus.CANCELLED},
    OrderStatus.PICKING: {OrderStatus.PACKED, OrderStatus.CANCELLED},
    OrderStatus.PACKED: {OrderStatus.SHIPPED, OrderStatus.PARTIALLY_SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.PARTIALLY_SHIPPED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: set(),
    OrderStatus.CANCELLED: set(),
}

ADMIN_ACTION_TO_STATUS = {
    "under_review": OrderStatus.UNDER_REVIEW,
    "approve": OrderStatus.APPROVED,
    "hold": OrderStatus.ON_HOLD,
    "release": OrderStatus.RELEASED_TO_WAREHOUSE,
    "picking": OrderStatus.PICKING,
    "packed": OrderStatus.PACKED,
    "ship_partial": OrderStatus.PARTIALLY_SHIPPED,
    "ship_full": OrderStatus.SHIPPED,
    "cancel": OrderStatus.CANCELLED,
}


ADMIN_ACTION_CONFIG = {
    "under_review": {"label": "Under Review", "btn_class": "btn-outline-secondary"},
    "approve": {"label": "Approve", "btn_class": "btn-outline-success"},
    "hold": {"label": "Hold", "btn_class": "btn-outline-warning"},
    "release": {"label": "Release", "btn_class": "btn-outline-primary"},
    "picking": {"label": "Picking", "btn_class": "btn-outline-primary"},
    "packed": {"label": "Packed", "btn_class": "btn-outline-primary"},
    "ship_partial": {"label": "Partially Shipped", "btn_class": "btn-outline-info"},
    "ship_full": {"label": "Shipped", "btn_class": "btn-success"},
    "cancel": {"label": "Cancel", "btn_class": "btn-outline-danger"},
}


def get_available_admin_actions(order: Order):
    allowed_statuses = ALLOWED_ORDER_TRANSITIONS.get(order.status, set())
    actions = []
    for action, status in ADMIN_ACTION_TO_STATUS.items():
        if status in allowed_statuses:
            config = ADMIN_ACTION_CONFIG[action]
            actions.append(
                {
                    "value": action,
                    "label": config["label"],
                    "btn_class": config["btn_class"],
                }
            )
    return actions


def transition_order_status(order: Order, new_status: str):
    allowed = ALLOWED_ORDER_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise ValidationError(f"Cannot transition order from {order.status} to {new_status}.")

    order.status = new_status
    if new_status == OrderStatus.SUBMITTED and not order.submitted_at:
        order.submitted_at = timezone.now()
    order.save(update_fields=["status", "submitted_at", "updated_at"])
    return order


def validate_order_item(customer, product, quantity, as_of=None):
    if quantity <= 0:
        raise ValidationError(f"Quantity must be positive for SKU {product.sku}.")

    approved = CustomerProduct.objects.filter(
        customer=customer, product=product, active=True
    ).exists()
    if not approved:
        raise ValidationError(f"Customer is not approved to order SKU {product.sku}.")

    price = get_active_customer_price(customer, product, as_of=as_of or date.today())
    if quantity < price.minimum_quantity:
        raise ValidationError(
            f"SKU {product.sku} requires minimum quantity {price.minimum_quantity}."
        )
    return price.unit_price


def validate_order_submission(order: Order):
    if not order.customer.is_active:
        raise ValidationError("Cannot submit order for inactive customer.")
    if not order.shipping_address or order.shipping_address.customer_id != order.customer_id:
        raise ValidationError("Order must have a valid customer shipping address.")
    if not order.shipping_address.is_active:
        raise ValidationError("Selected shipping address is inactive.")
    items = list(order.items.select_related("product"))
    if not items:
        raise ValidationError("Order must include at least one item.")

    as_of = date.today()
    for item in items:
        unit_price = validate_order_item(order.customer, item.product, item.quantity, as_of=as_of)
        if item.unit_price != unit_price:
            raise ValidationError(
                f"Order item price mismatch for SKU {item.product.sku}. "
                f"Expected {unit_price}, got {item.unit_price}."
            )


@transaction.atomic
def submit_order(order: Order):
    validate_order_submission(order)
    order.recalculate_totals()
    transition_order_status(order, OrderStatus.SUBMITTED)
    return order


@transaction.atomic
def add_item_to_order(order: Order, product, quantity):
    unit_price = validate_order_item(order.customer, product, quantity)
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        unit_price=unit_price,
        extended_price=unit_price * quantity,
    )
    order.recalculate_totals()
    return item
