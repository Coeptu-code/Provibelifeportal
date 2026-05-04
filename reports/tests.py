from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model

from customers.models import Customer, ShippingAddress
from invoicing.models import Invoice, InvoiceStatus
from orders.models import Order, OrderStatus
from products.models import Product


class AdminDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.ops_user = user_model.objects.create_user(
            username="ops_dash",
            password="pass1234",
            is_ops_user=True,
        )
        self.customer = Customer.objects.create(name="DashCo", payment_terms="NET_30")
        self.addr = ShippingAddress.objects.create(
            customer=self.customer,
            label="Main",
            line1="100 Main",
            city="Austin",
            state="TX",
            postal_code="78701",
        )
        self.product = Product.objects.create(name="Prod", case_quantity=1, active=True, sku="")

    def _make_order(self, status):
        return Order.objects.create(
            customer=self.customer,
            shipping_address=self.addr,
            status=status,
            total=Decimal("25.00"),
            subtotal=Decimal("25.00"),
        )

    def test_dashboard_shows_new_orders_and_open_status_counts(self):
        self._make_order(OrderStatus.SUBMITTED)
        self._make_order(OrderStatus.UNDER_REVIEW)
        self._make_order(OrderStatus.APPROVED)
        self._make_order(OrderStatus.SHIPPED)

        self.client.login(username="ops_dash", password="pass1234")
        response = self.client.get(reverse("admin_portal:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["new_orders_count"], 2)
        self.assertEqual(response.context["open_orders"], 3)
        self.assertEqual(len(response.context["new_orders"]), 2)

    def test_invoice_feed_includes_open_and_recently_closed_only(self):
        open_order = self._make_order(OrderStatus.SHIPPED)
        recent_paid_order = self._make_order(OrderStatus.SHIPPED)
        old_paid_order = self._make_order(OrderStatus.SHIPPED)

        Invoice.objects.create(
            order=open_order,
            customer=self.customer,
            invoice_number="INV-OPEN-1",
            subtotal=Decimal("10.00"),
            shipping_total=Decimal("0.00"),
            tax_total=Decimal("0.00"),
            total=Decimal("10.00"),
            status=InvoiceStatus.OPEN,
        )
        Invoice.objects.create(
            order=recent_paid_order,
            customer=self.customer,
            invoice_number="INV-PAID-NEW",
            subtotal=Decimal("12.00"),
            shipping_total=Decimal("0.00"),
            tax_total=Decimal("0.00"),
            total=Decimal("12.00"),
            status=InvoiceStatus.PAID,
            paid_at=timezone.now() - timedelta(days=2),
        )
        Invoice.objects.create(
            order=old_paid_order,
            customer=self.customer,
            invoice_number="INV-PAID-OLD",
            subtotal=Decimal("13.00"),
            shipping_total=Decimal("0.00"),
            tax_total=Decimal("0.00"),
            total=Decimal("13.00"),
            status=InvoiceStatus.PAID,
            paid_at=timezone.now() - timedelta(days=30),
        )

        self.client.login(username="ops_dash", password="pass1234")
        response = self.client.get(reverse("admin_portal:dashboard"))

        feed_numbers = [i.invoice_number for i in response.context["invoice_feed"]]
        self.assertIn("INV-OPEN-1", feed_numbers)
        self.assertIn("INV-PAID-NEW", feed_numbers)
        self.assertNotIn("INV-PAID-OLD", feed_numbers)
