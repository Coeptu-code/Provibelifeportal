from django.contrib import admin

from products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "active")
    search_fields = ("sku", "name")
    list_filter = ("active",)

    def get_fields(self, request, obj=None):
        base_fields = (
            "name",
            "description",
            "image",
            "case_quantity",
            "shipping_weight",
            "shipping_weight_unit",
            "shipping_length",
            "shipping_width",
            "shipping_height",
            "shipping_dimension_unit",
            "shipping_package_type",
            "active",
        )
        if obj:
            return ("sku",) + base_fields
        return base_fields

    readonly_fields = ("sku",)
