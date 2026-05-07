from django.contrib import admin
from django.contrib.auth import get_user_model

from customers.models import Customer, ShippingAddress

User = get_user_model()


class CustomerUserInline(admin.TabularInline):
    model = User
    fields = ("username", "email", "first_name", "last_name", "is_active")
    extra = 0
    show_change_link = True
    can_delete = False
    readonly_fields = ("username",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "payment_terms", "credit_limit", "is_active")
    list_filter = ("payment_terms", "is_active")
    search_fields = ("name", "shopify_customer_id", "stripe_customer_id")
    inlines = [CustomerUserInline]


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "label", "city", "state", "is_default", "is_active")
    list_filter = ("is_default", "is_active", "country", "state")
    search_fields = ("customer__name", "label", "city", "postal_code")
