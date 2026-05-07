from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import ops_required, sales_required
from pricing.forms import CustomerPriceForm, CustomerProductForm
from pricing.models import CustomerPrice


@sales_required
def admin_pricing(request):
    prices = CustomerPrice.objects.select_related("customer", "product").order_by(
        "customer__name", "product__sku", "-effective_date"
    )
    if request.user.role in ("sales_rep", "sales_lead"):
        prices = prices.filter(customer__in=request.user.get_accessible_customers())
    return render(request, "admin_portal/pricing.html", {"prices": prices})


@sales_required
def admin_customer_product_create(request):
    customer_id = request.GET.get("customer")
    if request.method == "POST":
        form = CustomerProductForm(request.POST)
        if form.is_valid():
            customer_product = form.save()
            messages.success(request, "Customer SKU approval created.")
            return redirect("admin_portal:customer_detail", pk=customer_product.customer_id)
    else:
        form = CustomerProductForm()
        if customer_id:
            form.fields["customer"].initial = customer_id
    return render(request, "admin_portal/customer_product_form.html", {"form": form})


@sales_required
def admin_customer_price_create(request):
    customer_id = request.GET.get("customer")
    if request.method == "POST":
        form = CustomerPriceForm(request.POST)
        if form.is_valid():
            customer_price = form.save()
            messages.success(request, "Customer pricing contract created.")
            return redirect("admin_portal:customer_detail", pk=customer_price.customer_id)
    else:
        form = CustomerPriceForm()
        if customer_id:
            form.fields["customer"].initial = customer_id
    return render(request, "admin_portal/customer_price_form.html", {
        "form": form,
        "form_title": "Add Customer Price Contract",
        "submit_label": "Save Pricing Contract",
        "cancel_url": f"/admin-portal/customers/{customer_id}/" if customer_id else "/admin-portal/pricing/",
    })


@sales_required
def admin_customer_price_edit(request, pk):
    price = get_object_or_404(CustomerPrice, pk=pk)
    if request.method == "POST":
        form = CustomerPriceForm(request.POST, instance=price)
        if form.is_valid():
            form.save()
            messages.success(request, "Pricing contract updated.")
            return redirect("admin_portal:customer_detail", pk=price.customer_id)
    else:
        form = CustomerPriceForm(instance=price)
    return render(request, "admin_portal/customer_price_form.html", {
        "form": form,
        "form_title": "Edit Pricing Contract",
        "submit_label": "Save Changes",
        "cancel_url": request.META.get("HTTP_REFERER", f"/admin-portal/customers/{price.customer_id}/"),
    })
# Create your views here.
