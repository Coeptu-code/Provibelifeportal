from django.contrib import admin

from orders.models import Order, OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "po_number", "requested_ship_date", "submitted_at")
    list_filter = ("status", "requested_ship_date")
    search_fields = ("id", "customer__name", "po_number")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "locked_unit_price", "extended_price")
    search_fields = ("order__id", "product__sku", "product__name")
