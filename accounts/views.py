from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import ops_required
from accounts.forms import CustomerUserCreateForm, CustomerUserUpdateForm

User = get_user_model()

@login_required
def root_redirect(request):
    if request.user.is_customer_user:
        return redirect("customers:dashboard")
    if request.user.is_ops_user or request.user.is_staff or request.user.is_superuser:
        return redirect("admin_portal:dashboard")
    return render(request, "registration/no_role.html")


@ops_required
def admin_customer_user_create(request):
    customer_id = request.GET.get("customer")
    if request.method == "POST":
        form = CustomerUserCreateForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, "Customer user created.")
                if user.customer_id:
                    return redirect("admin_portal:customer_detail", pk=user.customer_id)
                return redirect("admin_portal:customers")
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = CustomerUserCreateForm()
        if customer_id:
            form.fields["customer"].initial = int(customer_id)

    return render(
        request,
        "admin_portal/customer_user_form.html",
        {"form": form, "form_title": "Add Customer User", "submit_label": "Create User"},
    )


@ops_required
def admin_customer_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk, is_customer_user=True)
    if request.method == "POST":
        form = CustomerUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            try:
                updated_user = form.save()
                messages.success(request, "Customer user updated.")
                if updated_user.customer_id:
                    return redirect("admin_portal:customer_detail", pk=updated_user.customer_id)
                return redirect("admin_portal:customers")
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = CustomerUserUpdateForm(instance=user)

    return render(
        request,
        "admin_portal/customer_user_form.html",
        {"form": form, "form_title": "Edit Customer User", "submit_label": "Save User"},
    )
