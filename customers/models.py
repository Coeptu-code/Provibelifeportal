from django.db import models


class PaymentTerms(models.TextChoices):
    NET_15 = "NET_15", "Net 15"
    NET_30 = "NET_30", "Net 30"
    PREPAID = "PREPAID", "Prepaid"


class CarrierPreference(models.TextChoices):
    AUTO = "", "Auto (Best Available)"
    UPS = "UPS", "UPS"
    USPS = "USPS", "USPS"
    FEDEX = "FEDEX", "FedEx"
    DHL = "DHL", "DHL"


class Customer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    billing_address = models.TextField(blank=True)
    payment_terms = models.CharField(
        max_length=20,
        choices=PaymentTerms.choices,
        default=PaymentTerms.NET_30,
    )
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    preferred_carrier = models.CharField(
        max_length=20,
        choices=CarrierPreference.choices,
        default=CarrierPreference.AUTO,
        blank=True,
    )

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["payment_terms"]),
        ]

    def __str__(self):
        return self.name


class ShippingAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="shipping_addresses")
    label = models.CharField(max_length=100)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2, default="US")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("customer__name", "label")
        indexes = [
            models.Index(fields=["customer", "is_active"]),
            models.Index(fields=["customer", "is_default"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "label"],
                name="uniq_shipping_address_label_per_customer",
            )
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.label}"
# Create your models here.
