from django.db import models
from django.db.models import Q

from customers.models import Customer
from orders.models import Order


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    OPEN = "OPEN", "Open"
    PAID = "PAID", "Paid"
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
    OVERDUE = "OVERDUE", "Overdue"
    VOID = "VOID", "Void"


class ShippingQuoteStatus(models.TextChoices):
    NOT_QUOTED = "NOT_QUOTED", "Not Quoted"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class Invoice(models.Model):
    class InvoiceKind(models.TextChoices):
        PRIMARY = "PRIMARY", "Primary"
        ADJUSTMENT_DEBIT = "ADJUSTMENT_DEBIT", "Adjustment Debit"
        ADJUSTMENT_CREDIT = "ADJUSTMENT_CREDIT", "Adjustment Credit"

    class ShippingInputSource(models.TextChoices):
        ESTIMATED_API = "ESTIMATED_API", "Estimated API"
        MANUAL_OVERRIDE = "MANUAL_OVERRIDE", "Manual Override"
        FALLBACK_ZERO = "FALLBACK_ZERO", "Fallback Zero"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="invoices")
    parent_invoice = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="adjustments"
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_kind = models.CharField(
        max_length=24, choices=InvoiceKind.choices, default=InvoiceKind.PRIMARY
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=30, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT
    )
    shipping_carrier = models.CharField(max_length=50, blank=True)
    shipping_service = models.CharField(max_length=100, blank=True)
    shipping_rate_id = models.CharField(max_length=255, blank=True)
    shipping_currency = models.CharField(max_length=10, default="usd")
    shipping_quoted_at = models.DateTimeField(null=True, blank=True)
    shipping_quote_status = models.CharField(
        max_length=20,
        choices=ShippingQuoteStatus.choices,
        default=ShippingQuoteStatus.NOT_QUOTED,
    )
    shipping_input_source = models.CharField(
        max_length=20,
        choices=ShippingInputSource.choices,
        default=ShippingInputSource.FALLBACK_ZERO,
    )
    shipping_quote_reason = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    pdf_file = models.FileField(upload_to="invoices/", blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    stripe_hosted_invoice_url = models.URLField(blank=True)
    stripe_invoice_pdf = models.URLField(blank=True)
    shopify_draft_order_id = models.CharField(max_length=255, blank=True)
    shopify_order_id = models.CharField(max_length=255, blank=True)
    shopify_hosted_invoice_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["stripe_invoice_id"]),
            models.Index(fields=["shopify_draft_order_id"]),
            models.Index(fields=["shopify_order_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(invoice_kind="ADJUSTMENT_CREDIT") | Q(subtotal__gte=0),
                name="invoice_subtotal_valid_by_kind",
            ),
            models.CheckConstraint(
                condition=Q(shipping_total__gte=0), name="invoice_shipping_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(tax_total__gte=0), name="invoice_tax_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(invoice_kind="ADJUSTMENT_CREDIT") | Q(total__gte=0),
                name="invoice_total_valid_by_kind",
            ),
            models.UniqueConstraint(
                fields=["order", "invoice_kind"],
                condition=Q(invoice_kind="PRIMARY"),
                name="unique_primary_invoice_per_order",
            ),
        ]

    def __str__(self):
        return self.invoice_number

    @property
    def hosted_invoice_url(self):
        return self.shopify_hosted_invoice_url or self.stripe_hosted_invoice_url

    @property
    def external_invoice_id(self):
        return self.shopify_draft_order_id or self.stripe_invoice_id

    @property
    def external_invoice_pdf_url(self):
        return self.stripe_invoice_pdf
# Create your models here.
