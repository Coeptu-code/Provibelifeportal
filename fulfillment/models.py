from django.db import models

from orders.models import Order


class ShipmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PICKING = "PICKING", "Picking"
    PACKED = "PACKED", "Packed"
    SHIPPED = "SHIPPED", "Shipped"


class Shipment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")
    carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=255, blank=True)
    shopify_fulfillment_id = models.CharField(max_length=255, blank=True)
    shopify_fulfillment_order_id = models.CharField(max_length=255, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=50, choices=ShipmentStatus.choices, default=ShipmentStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["shipped_at"]),
            models.Index(fields=["order", "status"]),
        ]

    def __str__(self):
        return f"Shipment {self.pk} for Order {self.order_id}"
# Create your models here.
