from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from customers.models import Customer


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER_USER = "customer_user", "Customer User"
        WAREHOUSE_STAFF = "warehouse_staff", "Warehouse Staff"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.ADMIN,
        db_index=True,
    )
    is_customer_user = models.BooleanField(default=False)
    is_warehouse_staff = models.BooleanField(default=False)
    is_ops_user = models.BooleanField(default=False)
    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )

    class Meta:
        ordering = ("username",)
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if self.role == self.Role.CUSTOMER_USER and not self.customer:
            raise ValidationError("Customer users must be linked to a customer account.")
        if self.role != self.Role.CUSTOMER_USER and self.customer_id:
            raise ValidationError("Only customer users may be linked to a customer account.")

    def _sync_role_flags(self):
        self.is_customer_user = self.role == self.Role.CUSTOMER_USER
        self.is_warehouse_staff = self.role == self.Role.WAREHOUSE_STAFF
        self.is_ops_user = self.role in {self.Role.WAREHOUSE_STAFF, self.Role.ADMIN}
        if self.role in {self.Role.ADMIN, self.Role.WAREHOUSE_STAFF}:
            self.is_staff = True

    def save(self, *args, **kwargs):
        self._sync_role_flags()
        self.full_clean()
        return super().save(*args, **kwargs)

# Create your models here.
