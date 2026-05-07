from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Index
from django.utils import timezone
import uuid

from customers.models import Customer


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER_USER = "customer_user", "Customer User"
        WAREHOUSE_STAFF = "warehouse_staff", "Warehouse Staff"
        SALES_REP = "sales_rep", "Sales Rep"
        SALES_LEAD = "sales_lead", "Sales Lead"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.ADMIN,
        db_index=True,
    )
    is_customer_user = models.BooleanField(default=False)
    is_warehouse_staff = models.BooleanField(default=False)
    is_sales_rep = models.BooleanField(default=False)
    is_sales_lead = models.BooleanField(default=False)
    is_ops_user = models.BooleanField(default=False)
    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )
    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
        limit_choices_to={"role": "sales_lead"},
    )
    invited_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invited_users",
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
        if self.role == self.Role.SALES_REP and self.manager and self.manager.role != self.Role.SALES_LEAD:
            raise ValidationError("Sales reps must report to a sales lead.")

    def _sync_role_flags(self):
        if self.role == self.Role.ADMIN and self.customer_id and self.is_customer_user:
            self.role = self.Role.CUSTOMER_USER
        elif self.role == self.Role.ADMIN and self.is_warehouse_staff:
            self.role = self.Role.WAREHOUSE_STAFF

        self.is_customer_user = self.role == self.Role.CUSTOMER_USER
        self.is_warehouse_staff = self.role == self.Role.WAREHOUSE_STAFF
        self.is_sales_rep = self.role == self.Role.SALES_REP
        self.is_sales_lead = self.role == self.Role.SALES_LEAD
        self.is_ops_user = self.role in {self.Role.WAREHOUSE_STAFF, self.Role.SALES_REP, self.Role.SALES_LEAD, self.Role.ADMIN}
        if self.role in {self.Role.ADMIN, self.Role.WAREHOUSE_STAFF, self.Role.SALES_REP, self.Role.SALES_LEAD}:
            self.is_staff = True

    def save(self, *args, **kwargs):
        self._sync_role_flags()
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_accessible_customers(self):
        """Return Customer queryset based on user role."""
        if self.role == self.Role.ADMIN:
            return Customer.objects.all()
        if self.role == self.Role.SALES_LEAD:
            return Customer.objects.filter(Q(sales_rep=self) | Q(sales_rep__manager=self))
        if self.role == self.Role.SALES_REP:
            return Customer.objects.filter(sales_rep=self)
        return Customer.objects.none()

    def get_initials(self):
        return (self.first_name[0] if self.first_name else '') + (self.last_name[0] if self.last_name else '') or self.username[0].upper()


class CustomerInvitation(models.Model):
    email = models.EmailField()
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="invitations"
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_invitations",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            Index(fields=["token"]),
            Index(fields=["email", "customer"]),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.accepted_at and timezone.now() < self.expires_at


class RetailerLead(models.Model):
    """
    A lightweight record representing a potential retailer signup that was
    contacted via a marketing email. This is not an auth token; it exists so
    we can tie account-creation tokens to a stable recipient identity.
    """

    email = models.EmailField(unique=True)
    store_name = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_retailer_leads",
    )
    created_customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="retailer_leads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return self.email


class RetailerAccountCreationToken(models.Model):
    lead = models.ForeignKey(
        RetailerLead,
        on_delete=models.CASCADE,
        related_name="account_tokens",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_retailer_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            Index(fields=["token"]),
            Index(fields=["expires_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Keep expiry behavior consistent with CustomerInvitation policy.
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return not self.used_at and timezone.now() < self.expires_at


class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=100)
    detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [Index(fields=["user", "created_at"])]
