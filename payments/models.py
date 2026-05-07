from django.db import models

from invoicing.models import Invoice


class PaymentMethod(models.TextChoices):
    ACH = "ACH", "ACH"
    WIRE = "WIRE", "Wire"
    CHECK = "CHECK", "Check"
    SHOPIFY = "SHOPIFY", "Shopify"
    STRIPE = "STRIPE", "Stripe"
    OTHER = "OTHER", "Other"


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.OTHER)
    reference_number = models.CharField(max_length=100, blank=True)
    received_at = models.DateTimeField()
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    shopify_payment_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-received_at",)
        indexes = [
            models.Index(fields=["invoice", "received_at"]),
            models.Index(fields=["method"]),
            models.Index(fields=["stripe_payment_intent_id"]),
            models.Index(fields=["shopify_payment_id"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_amount_gt_zero"),
        ]

    def __str__(self):
        return f"Payment {self.id} for {self.invoice.invoice_number}"


class StripeWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at",)
        indexes = [
            models.Index(fields=["event_type", "received_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"


class ShopifyWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    shop_domain = models.CharField(max_length=255, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at",)
        indexes = [
            models.Index(fields=["event_type", "received_at"]),
            models.Index(fields=["shop_domain", "received_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"
