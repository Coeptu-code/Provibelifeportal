from django.shortcuts import render

from accounts.decorators import ops_required
from fulfillment.models import Shipment
from orders.models import Order, OrderStatus

FULFILLMENT_STATUSES = [
    OrderStatus.RELEASED_TO_WAREHOUSE,
    OrderStatus.PICKING,
    OrderStatus.PACKED,
    OrderStatus.PARTIALLY_SHIPPED,
]


@ops_required
def admin_fulfillment_queue(request):
    orders = Order.objects.select_related("customer").filter(status__in=FULFILLMENT_STATUSES)
    return render(request, "admin_portal/fulfillment_queue.html", {"orders": orders})


@ops_required
def admin_shipments(request):
    shipments = Shipment.objects.select_related("order", "order__customer").order_by("-created_at")
    return render(request, "admin_portal/shipments.html", {"shipments": shipments})


@ops_required
def admin_pick_ticket(request):
    return render(request, "admin_portal/pick_ticket.html")
