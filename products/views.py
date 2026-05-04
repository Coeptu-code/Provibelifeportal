from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import ops_required
from products.forms import ProductForm
from products.models import Product


@ops_required
def admin_products(request):
    products = Product.objects.all().order_by("sku")
    return render(request, "admin_portal/products.html", {"products": products})


@ops_required
def admin_product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product created.")
            return redirect("admin_portal:products")
    else:
        form = ProductForm()
    return render(
        request,
        "admin_portal/product_form.html",
        {
            "form": form,
            "next_sku": Product.peek_next_sku(),
            "form_title": "Add Product",
            "submit_label": "Create Product",
        },
    )


@ops_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect("admin_portal:products")
    else:
        form = ProductForm(instance=product)
    return render(
        request,
        "admin_portal/product_form.html",
        {
            "form": form,
            "product": product,
            "form_title": "Edit Product",
            "submit_label": "Save Changes",
        },
    )


@ops_required
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            product.delete()
            messages.success(request, "Product deleted.")
        except ProtectedError:
            messages.error(
                request,
                "Cannot delete this product because it is referenced by existing orders.",
            )
        return redirect("admin_portal:products")
    return render(request, "admin_portal/product_confirm_delete.html", {"product": product})
