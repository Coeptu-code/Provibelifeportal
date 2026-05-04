from django.contrib import admin

from customers.models import Customer, ShippingAddress


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "payment_terms", "credit_limit", "is_active")
    list_filter = ("payment_terms", "is_active")
    search_fields = ("name", "stripe_customer_id")


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "label", "city", "state", "is_default", "is_active")
    list_filter = ("is_default", "is_active", "country", "state")
    search_fields = ("customer__name", "label", "city", "postal_code")
