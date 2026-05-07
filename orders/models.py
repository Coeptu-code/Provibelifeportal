from django.db import models
from django.db.models import Q, Sum

from customers.models import Customer, ShippingAddress
from products.models import Product


class OrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    ON_HOLD = "ON_HOLD", "On Hold"
    RELEASED_TO_WAREHOUSE = "RELEASED_TO_WAREHOUSE", "Released to Warehouse"
    PICKING = "PICKING", "Picking"
    PACKED = "PACKED", "Packed"
    SHIPPED = "SHIPPED", "Shipped"
    PARTIALLY_SHIPPED = "PARTIALLY_SHIPPED", "Partially Shipped"
    CANCELLED = "CANCELLED", "Cancelled"


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    shipping_address = models.ForeignKey(
        ShippingAddress, null=True, blank=True, on_delete=models.PROTECT, related_name="orders"
    )
    po_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=50, choices=OrderStatus.choices, default=OrderStatus.DRAFT
    )
    requested_ship_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shopify_order_id = models.CharField(max_length=255, blank=True)
    shopify_order_name = models.CharField(max_length=100, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["submitted_at"]),
        ]

    def recalculate_totals(self):
        subtotal = self.items.aggregate(total=Sum("extended_price"))["total"] or 0
        self.subtotal = subtotal
        self.total = subtotal
        self.save(update_fields=["subtotal", "total", "updated_at"])

    def __str__(self):
        return f"Order {self.pk} - {self.customer.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    locked_unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    extended_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ("order_id", "product__sku")
        indexes = [
            models.Index(fields=["order", "product"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="order_item_quantity_gt_zero"
            ),
            models.CheckConstraint(
                condition=Q(locked_unit_price__gte=0), name="order_item_locked_price_non_negative"
            ),
            models.UniqueConstraint(
                fields=["order", "product"], name="uniq_order_product"
            ),
        ]

    def save(self, *args, **kwargs):
        if self.locked_unit_price == 0 and self.unit_price:
            self.locked_unit_price = self.unit_price
        self.unit_price = self.locked_unit_price
        self.extended_price = self.quantity * self.unit_price
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} / {self.product.sku} x {self.quantity}"
# Create your models here.
