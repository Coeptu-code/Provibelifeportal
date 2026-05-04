from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from customers.models import Customer
from products.models import Product


class CustomerProduct(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="product_approvals")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="customer_approvals")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("customer__name", "product__sku")
        indexes = [
            models.Index(fields=["customer", "active"]),
            models.Index(fields=["product", "active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"], name="uniq_customer_product"
            )
        ]

    def __str__(self):
        return f"{self.customer} / {self.product}"


class CustomerPrice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="price_contracts")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="customer_prices")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_quantity = models.PositiveIntegerField(default=1)
    effective_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("customer__name", "product__sku", "-effective_date")
        indexes = [
            models.Index(fields=["customer", "product"]),
            models.Index(fields=["effective_date", "expiration_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product", "effective_date"],
                name="uniq_customer_price_effective_start",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0), name="customer_price_unit_price_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(minimum_quantity__gt=0), name="customer_price_minimum_qty_gt_zero"
            ),
        ]

    def clean(self):
        if self.expiration_date and self.expiration_date < self.effective_date:
            raise ValidationError("Expiration date cannot be before effective date.")

        overlapping = CustomerPrice.objects.filter(
            customer=self.customer,
            product=self.product,
        ).exclude(pk=self.pk)

        overlapping = overlapping.filter(
            Q(expiration_date__isnull=True) | Q(expiration_date__gte=self.effective_date)
        )
        if self.expiration_date:
            overlapping = overlapping.filter(effective_date__lte=self.expiration_date)

        if overlapping.exists():
            raise ValidationError(
                "Overlapping active pricing exists for this customer and product."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} / {self.product} @ {self.unit_price}"
# Create your models here.
