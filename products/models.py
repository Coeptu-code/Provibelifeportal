import re

from django.db import IntegrityError, models, transaction


class Product(models.Model):
    SKU_PREFIX = "PVB-"
    SKU_START = 100001

    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    case_quantity = models.PositiveIntegerField(default=1)
    shipping_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_weight_unit = models.CharField(
        max_length=8,
        choices=[("oz", "Ounces"), ("lb", "Pounds")],
        default="oz",
    )
    shipping_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_dimension_unit = models.CharField(
        max_length=8,
        choices=[("in", "Inches"), ("cm", "Centimeters")],
        default="in",
    )
    shipping_package_type = models.CharField(max_length=50, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sku",)
        indexes = [
            models.Index(fields=["active"]),
            models.Index(fields=["name"]),
        ]

    @classmethod
    def _next_sku_value(cls):
        pattern = re.compile(rf"^{re.escape(cls.SKU_PREFIX)}(\d+)$")
        max_value = cls.SKU_START - 1

        for sku in cls.objects.filter(sku__startswith=cls.SKU_PREFIX).values_list("sku", flat=True):
            match = pattern.match(sku)
            if not match:
                continue
            max_value = max(max_value, int(match.group(1)))
        return max_value + 1

    @classmethod
    def peek_next_sku(cls):
        return f"{cls.SKU_PREFIX}{cls._next_sku_value()}"

    def save(self, *args, **kwargs):
        if self.sku:
            return super().save(*args, **kwargs)

        for _ in range(10):
            self.sku = f"{self.SKU_PREFIX}{self._next_sku_value()}"
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.sku = ""
        raise IntegrityError("Unable to auto-generate a unique SKU after multiple attempts.")

    def __str__(self):
        return f"{self.sku} - {self.name}"

    @property
    def display_image_url(self):
        if self.image_url:
            return self.image_url
        if self.image:
            try:
                return self.image.url
            except ValueError:
                return ""
        return ""
# Create your models here.
