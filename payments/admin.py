from django.contrib import admin

from payments.models import Payment, StripeWebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "amount", "method", "reference_number", "received_at")
    list_filter = ("method", "received_at")
    search_fields = ("invoice__invoice_number", "reference_number", "stripe_payment_intent_id")


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "received_at", "processed_at")
    list_filter = ("event_type",)
    search_fields = ("event_id", "event_type")
