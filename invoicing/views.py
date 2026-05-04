from django.shortcuts import get_object_or_404, render

from accounts.decorators import customer_required, ops_required
from invoicing.models import Invoice


@customer_required
def customer_invoices(request):
    invoices = Invoice.objects.filter(customer=request.user.customer).order_by("-created_at")
    return render(request, "customer/invoices.html", {"invoices": invoices})


@customer_required
def customer_invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, customer=request.user.customer)
    return render(request, "customer/invoice_detail.html", {"invoice": invoice})


@ops_required
def admin_invoices(request):
    invoices = Invoice.objects.select_related("customer", "order").order_by("-created_at")
    return render(request, "admin_portal/invoices.html", {"invoices": invoices})


@ops_required
def admin_invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("order", "customer"), pk=pk)
    return render(request, "admin_portal/invoice_detail.html", {"invoice": invoice})
