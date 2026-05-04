from django.contrib import admin

from pricing.models import CustomerPrice, CustomerProduct


@admin.register(CustomerProduct)
class CustomerProductAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "active")
    list_filter = ("active",)
    search_fields = ("customer__name", "product__sku", "product__name")


@admin.register(CustomerPrice)
class CustomerPriceAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "product",
        "unit_price",
        "minimum_quantity",
        "effective_date",
        "expiration_date",
    )
    list_filter = ("effective_date", "expiration_date")
    search_fields = ("customer__name", "product__sku", "product__name")
