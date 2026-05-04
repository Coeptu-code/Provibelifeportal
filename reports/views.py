from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import ops_required
from invoicing.models import Invoice, InvoiceStatus
from orders.models import Order, OrderStatus


@ops_required
def admin_dashboard(request):
    now = timezone.now()
    recent_closed_cutoff = now - timedelta(days=14)

    open_order_statuses = [
        OrderStatus.SUBMITTED,
        OrderStatus.UNDER_REVIEW,
        OrderStatus.APPROVED,
        OrderStatus.ON_HOLD,
        OrderStatus.RELEASED_TO_WAREHOUSE,
        OrderStatus.PICKING,
        OrderStatus.PACKED,
        OrderStatus.PARTIALLY_SHIPPED,
    ]
    new_order_statuses = [OrderStatus.SUBMITTED, OrderStatus.UNDER_REVIEW]
    open_invoice_statuses = [
        InvoiceStatus.DRAFT,
        InvoiceStatus.SENT,
        InvoiceStatus.OPEN,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.OVERDUE,
    ]

    open_order_status_map = {
        row["status"]: row["count"]
        for row in Order.objects.filter(status__in=open_order_statuses)
        .values("status")
        .annotate(count=Count("id"))
    }
    open_order_status_cards = [
        {"status": status, "count": open_order_status_map.get(status, 0)}
        for status in open_order_statuses
    ]

    new_orders = (
        Order.objects.select_related("customer", "shipping_address")
        .filter(status__in=new_order_statuses)
        .order_by("-created_at")[:8]
    )
    invoice_feed = (
        Invoice.objects.select_related("customer", "order")
        .filter(
            Q(status__in=open_invoice_statuses)
            | Q(status=InvoiceStatus.PAID, paid_at__gte=recent_closed_cutoff)
        )
        .order_by("-created_at")[:10]
    )

    context = {
        "open_orders": Order.objects.filter(status__in=open_order_statuses).count(),
        "new_orders_count": Order.objects.filter(status__in=new_order_statuses).count(),
        "submitted_orders": Order.objects.filter(status=OrderStatus.SUBMITTED).count(),
        "fulfillment_orders": Order.objects.filter(
            status__in=[
                OrderStatus.RELEASED_TO_WAREHOUSE,
                OrderStatus.PICKING,
                OrderStatus.PACKED,
                OrderStatus.PARTIALLY_SHIPPED,
            ]
        ).count(),
        "open_invoices": Invoice.objects.filter(status__in=open_invoice_statuses).count(),
        "open_order_status_cards": open_order_status_cards,
        "new_orders": new_orders,
        "invoice_feed": invoice_feed,
        "recent_closed_days": 14,
    }
    return render(request, "admin_portal/dashboard.html", context)


@ops_required
def admin_payments(request):
    invoices = Invoice.objects.select_related("customer").order_by("-created_at")[:100]
    return render(request, "admin_portal/payments.html", {"invoices": invoices})


@ops_required
def admin_reports(request):
    return render(request, "admin_portal/reports.html")
