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
    phone = models.CharField(max_length=50, blank=True)
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


class RetailerMarketingPageToken(models.Model):
    class PageSlug(models.TextChoices):
        FREE_SAMPLE = "free-sample", "Free Sample"

    lead = models.ForeignKey(
        RetailerLead,
        on_delete=models.CASCADE,
        related_name="marketing_page_tokens",
    )
    page_slug = models.CharField(
        max_length=64,
        choices=PageSlug.choices,
        default=PageSlug.FREE_SAMPLE,
    )
    source = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional campaign/template source label.",
    )
    is_test = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_marketing_page_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    first_clicked_at = models.DateTimeField(null=True, blank=True)
    last_clicked_at = models.DateTimeField(null=True, blank=True)
    click_count = models.PositiveIntegerField(default=0)
    last_click_ip = models.GenericIPAddressField(null=True, blank=True)
    last_click_user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            Index(fields=["token"]),
            Index(fields=["page_slug", "created_at"]),
            Index(fields=["last_clicked_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return timezone.now() < self.expires_at

    def mark_clicked(self, *, ip_address: str | None, user_agent: str | None) -> None:
        now = timezone.now()
        if not self.first_clicked_at:
            self.first_clicked_at = now
        self.last_clicked_at = now
        self.click_count = (self.click_count or 0) + 1
        self.last_click_ip = ip_address or None
        self.last_click_user_agent = (user_agent or "")[:2000]
        self.save(
            update_fields=[
                "first_clicked_at",
                "last_clicked_at",
                "click_count",
                "last_click_ip",
                "last_click_user_agent",
            ]
        )


class FreeSampleSubmission(models.Model):
    lead = models.OneToOneField(
        RetailerLead,
        on_delete=models.CASCADE,
        related_name="free_sample_submission",
    )
    token = models.ForeignKey(
        RetailerMarketingPageToken,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="free_sample_submissions",
    )
    source = models.CharField(max_length=120, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    business_name = models.CharField(max_length=255)
    shipping_address = models.TextField()
    business_type = models.CharField(max_length=255)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            Index(fields=["source"]),
            Index(fields=["submitted_at"]),
            Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.submitted_at.isoformat()})"


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
