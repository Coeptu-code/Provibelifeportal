from django.contrib import admin

from invoicing.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "order", "customer", "status", "total", "due_date")
    list_filter = ("status", "due_date")
    search_fields = ("invoice_number", "customer__name", "order__id", "stripe_invoice_id")
