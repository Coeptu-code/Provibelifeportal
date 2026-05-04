from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import customer_required, ops_required
from accounts.models import User
from customers.forms import AdminShippingAddressForm, CustomerForm, ShippingAddressForm
from customers.models import Customer, ShippingAddress
from invoicing.models import Invoice
from orders.models import Order
from pricing.models import CustomerPrice, CustomerProduct


@customer_required
def dashboard(request):
    customer = request.user.customer
    context = {
        "order_count": Order.objects.filter(customer=customer).count(),
        "open_invoice_count": Invoice.objects.filter(customer=customer).exclude(status="PAID").count(),
    }
    return render(request, "customer/dashboard.html", context)


@customer_required
def shipping_addresses(request):
    customer = request.user.customer
    addresses = customer.shipping_addresses.order_by("-is_default", "label")
    return render(request, "customer/shipping_addresses.html", {"addresses": addresses})


@customer_required
def shipping_address_new(request):
    customer = request.user.customer
    if request.method == "POST":
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = customer
            if address.is_default:
                customer.shipping_addresses.update(is_default=False)
            address.save()
            messages.success(request, "Shipping address added.")
            return redirect("customers:shipping_addresses")
    else:
        form = ShippingAddressForm()
    return render(request, "customer/shipping_address_new.html", {"form": form})


@customer_required
def account(request):
    return render(request, "customer/account.html")


@ops_required
def admin_customers(request):
    customers = Customer.objects.all().order_by("name")
    return render(request, "admin_portal/customers.html", {"customers": customers})


@ops_required
def admin_customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer_products = CustomerProduct.objects.filter(customer=customer).select_related("product")
    customer_prices = CustomerPrice.objects.filter(customer=customer).select_related("product")
    return render(
        request,
        "admin_portal/customer_detail.html",
        {
            "customer": customer,
            "customer_products": customer_products,
            "customer_prices": customer_prices,
            "customer_users": User.objects.filter(customer=customer, is_customer_user=True).order_by(
                "username"
            ),
            "recent_orders": Order.objects.filter(customer=customer).order_by("-created_at")[:20],
        },
    )


@ops_required
def admin_customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, "Customer created.")
            return redirect("admin_portal:customer_detail", pk=customer.pk)
    else:
        form = CustomerForm()
    return render(request, "admin_portal/customer_form.html", {"form": form})


@ops_required
def admin_shipping_address_create(request):
    customer_id = request.GET.get("customer")
    if request.method == "POST":
        form = AdminShippingAddressForm(request.POST)
        if form.is_valid():
            shipping_address = form.save()
            if shipping_address.is_default:
                ShippingAddress.objects.filter(customer=shipping_address.customer).exclude(
                    pk=shipping_address.pk
                ).update(is_default=False)
            messages.success(request, "Shipping address created.")
            return redirect("admin_portal:customer_detail", pk=shipping_address.customer_id)
    else:
        form = AdminShippingAddressForm()
        if customer_id:
            form.fields["customer"].initial = customer_id
    return render(request, "admin_portal/shipping_address_form.html", {"form": form})


@ops_required
def admin_shipping_address_edit(request, pk):
    address = get_object_or_404(ShippingAddress, pk=pk)
    if request.method == "POST":
        form = AdminShippingAddressForm(request.POST, instance=address)
        if form.is_valid():
            shipping_address = form.save()
            if shipping_address.is_default:
                ShippingAddress.objects.filter(customer=shipping_address.customer).exclude(
                    pk=shipping_address.pk
                ).update(is_default=False)
            messages.success(request, "Shipping address updated.")
            return redirect("admin_portal:customer_detail", pk=shipping_address.customer_id)
    else:
        form = AdminShippingAddressForm(instance=address)
    return render(request, "admin_portal/shipping_address_form.html", {"form": form})
