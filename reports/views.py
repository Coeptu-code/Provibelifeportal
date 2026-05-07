from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import admin_required, ops_required, sales_required
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

    orders_base = Order.objects.all()
    invoices_base = Invoice.objects.all()

    if request.user.role in ("sales_rep", "sales_lead"):
        accessible_customers = request.user.get_accessible_customers()
        orders_base = orders_base.filter(customer__in=accessible_customers)
        invoices_base = invoices_base.filter(customer__in=accessible_customers)

    open_order_status_map = {
        row["status"]: row["count"]
        for row in orders_base.filter(status__in=open_order_statuses, archived_at__isnull=True)
        .values("status")
        .annotate(count=Count("id"))
    }
    open_order_status_cards = [
        {"status": status, "count": open_order_status_map.get(status, 0)}
        for status in open_order_statuses
    ]

    new_orders = (
        orders_base.select_related("customer", "shipping_address")
        .filter(status__in=new_order_statuses)
        .order_by("-created_at")[:8]
    )
    invoice_feed = (
        invoices_base.select_related("customer", "order")
        .filter(
            Q(status__in=open_invoice_statuses)
            | Q(status=InvoiceStatus.PAID, paid_at__gte=recent_closed_cutoff)
        )
        .order_by("-created_at")[:10]
    )

    context = {
        "open_orders": orders_base.filter(status__in=open_order_statuses, archived_at__isnull=True).count(),
        "new_orders_count": orders_base.filter(status__in=new_order_statuses, archived_at__isnull=True).count(),
        "submitted_orders": orders_base.filter(status=OrderStatus.SUBMITTED, archived_at__isnull=True).count(),
        "fulfillment_orders": orders_base.filter(
            status__in=[
                OrderStatus.RELEASED_TO_WAREHOUSE,
                OrderStatus.PICKING,
                OrderStatus.PACKED,
                OrderStatus.PARTIALLY_SHIPPED,
            ],
            archived_at__isnull=True,
        ).count(),
        "open_invoices": invoices_base.filter(status__in=open_invoice_statuses).count(),
        "open_order_status_cards": open_order_status_cards,
        "new_orders": new_orders,
        "invoice_feed": invoice_feed,
        "recent_closed_days": 14,
    }
    return render(request, "admin_portal/dashboard.html", context)


@sales_required
def admin_payments(request):
    invoices = Invoice.objects.select_related("customer").order_by("-created_at")[:100]
    if request.user.role in ("sales_rep", "sales_lead"):
        invoices = invoices.filter(customer__in=request.user.get_accessible_customers())
    return render(request, "admin_portal/payments.html", {"invoices": invoices})


@admin_required
def admin_reports(request):
    return render(request, "admin_portal/reports.html")
