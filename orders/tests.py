from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from customers.models import Customer, ShippingAddress
from fulfillment.models import Shipment
from invoicing.models import Invoice
from orders.models import Order, OrderItem, OrderStatus
from orders.services import submit_order, transition_order_status, validate_order_item
from pricing.models import CustomerPrice, CustomerProduct
from products.models import Product


class OrderRuleTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Acme", payment_terms="NET_30")
        self.address = ShippingAddress.objects.create(
            customer=self.customer,
            label="Main",
            line1="123 Main",
            city="Austin",
            state="TX",
            postal_code="78701",
            is_default=True,
        )
        self.product = Product.objects.create(sku="SKU-1", name="Omega")
        CustomerProduct.objects.create(customer=self.customer, product=self.product, active=True)
        CustomerPrice.objects.create(
            customer=self.customer,
            product=self.product,
            unit_price=Decimal("12.50"),
            minimum_quantity=3,
            effective_date=date(2026, 1, 1),
        )

    def test_min_quantity_enforced(self):
        with self.assertRaises(ValidationError):
            validate_order_item(self.customer, self.product, 1)

    def test_unapproved_product_blocked(self):
        unapproved = Product.objects.create(sku="SKU-UN", name="Unapproved")
        with self.assertRaises(ValidationError):
            validate_order_item(self.customer, unapproved, 5)

    def test_invalid_status_transition_rejected(self):
        order = Order.objects.create(customer=self.customer, shipping_address=self.address)
        with self.assertRaises(ValidationError):
            transition_order_status(order, OrderStatus.SHIPPED)

    def test_submit_flow_sets_submitted(self):
        order = Order.objects.create(customer=self.customer, shipping_address=self.address)
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=3,
            unit_price=Decimal("12.50"),
            extended_price=Decimal("37.50"),
        )
        submit_order(order)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.SUBMITTED)
        self.assertIsNotNone(order.submitted_at)
        self.assertEqual(order.total, Decimal("37.50"))


@override_settings(EASYPOST_ENABLED=True, EASYPOST_API_KEY="EZTK_TEST")
class OrderViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = Customer.objects.create(name="Bravo", payment_terms="NET_30")
        self.address = ShippingAddress.objects.create(
            customer=self.customer,
            label="Dock",
            line1="45 Market",
            city="Dallas",
            state="TX",
            postal_code="75001",
        )
        self.product = Product.objects.create(sku="SKU-2", name="Vitamin D")
        self.unapproved_product = Product.objects.create(sku="SKU-3", name="Hidden Product")
        CustomerProduct.objects.create(customer=self.customer, product=self.product, active=True)
        CustomerPrice.objects.create(
            customer=self.customer,
            product=self.product,
            unit_price=Decimal("8.00"),
            minimum_quantity=2,
            effective_date=date(2026, 1, 1),
        )
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="customer1",
            password="pass1234",
            is_customer_user=True,
            customer=self.customer,
        )

    def test_customer_submit_order_uses_system_price(self):
        self.client.login(username="customer1", password="pass1234")
        quote = SimpleNamespace(
            amount=Decimal("9.95"),
            currency="usd",
            carrier="UPS",
            service="Ground",
            rate_id="rate_v1",
            raw_ref="shp_v1",
        )
        with patch("orders.views.quote_shipping_for_order", return_value=quote):
            verify_response = self.client.post(
                reverse("customers:order_new"),
                {
                    "action": "verify",
                    "po_number": "PO-123",
                    "shipping_address": str(self.address.id),
                    "requested_ship_date": "2026-05-20",
                    "product_id": str(self.product.id),
                    f"quantity_{self.product.id}": "2",
                    f"quantity_{self.unapproved_product.id}": "99",
                },
            )

        self.assertEqual(verify_response.status_code, 200)
        self.assertContains(verify_response, "Verify Order")
        session_drafts = self.client.session.get("customer_order_drafts", {})
        self.assertEqual(len(session_drafts), 1)
        draft_token = list(session_drafts.keys())[0]

        with patch("orders.views.quote_shipping_for_order", return_value=quote):
            confirm_response = self.client.post(
                reverse("customers:order_new"),
                {"action": "confirm", "draft_token": draft_token},
            )
        self.assertEqual(confirm_response.status_code, 302)
        order = Order.objects.get(customer=self.customer)
        item = order.items.get()
        self.assertEqual(order.status, OrderStatus.SUBMITTED)
        self.assertEqual(item.unit_price, Decimal("8.00"))
        self.assertEqual(item.product_id, self.product.id)

    def test_order_new_shows_only_approved_products(self):
        self.client.login(username="customer1", password="pass1234")
        response = self.client.get(reverse("customers:order_new"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.sku)
        self.assertNotContains(response, self.unapproved_product.sku)

    def test_submit_with_unapproved_product_is_rejected(self):
        self.client.login(username="customer1", password="pass1234")
        response = self.client.post(
            reverse("customers:order_new"),
            {
                "action": "verify",
                "po_number": "PO-999",
                "shipping_address": str(self.address.id),
                "product_id": str(self.unapproved_product.id),
                f"quantity_{self.unapproved_product.id}": "2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not approved")
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)

    def test_submit_with_quantity_below_minimum_is_rejected(self):
        self.client.login(username="customer1", password="pass1234")
        response = self.client.post(
            reverse("customers:order_new"),
            {
                "action": "verify",
                "shipping_address": str(self.address.id),
                "product_id": str(self.product.id),
                f"quantity_{self.product.id}": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "minimum quantity")
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)

    def test_submit_with_missing_shipping_address_is_rejected(self):
        self.client.login(username="customer1", password="pass1234")
        response = self.client.post(
            reverse("customers:order_new"),
            {
                "action": "verify",
                "product_id": str(self.product.id),
                f"quantity_{self.product.id}": "2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "shipping_address", "This field is required.")
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)

    def test_verify_shows_shipping_breakdown(self):
        self.client.login(username="customer1", password="pass1234")
        quote = SimpleNamespace(
            amount=Decimal("11.25"),
            currency="usd",
            carrier="UPS",
            service="Ground",
            rate_id="rate_verify",
            raw_ref="shp_verify",
        )
        with patch("orders.views.quote_shipping_for_order", return_value=quote):
            response = self.client.post(
                reverse("customers:order_new"),
                {
                    "action": "verify",
                    "shipping_address": str(self.address.id),
                    "product_id": str(self.product.id),
                    f"quantity_{self.product.id}": "2",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estimated Shipping")
        self.assertContains(response, "Estimated Total")
        self.assertContains(response, "UPS Ground")

    def test_confirm_with_tampered_token_is_rejected(self):
        self.client.login(username="customer1", password="pass1234")
        response = self.client.post(
            reverse("customers:order_new"),
            {"action": "confirm", "draft_token": "bad-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "verification expired")
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)

    def test_requote_change_requires_resubmit_without_creating_order(self):
        self.client.login(username="customer1", password="pass1234")
        quote_first = SimpleNamespace(
            amount=Decimal("8.00"),
            currency="usd",
            carrier="UPS",
            service="Ground",
            rate_id="rate_1",
            raw_ref="shp_1",
        )
        quote_second = SimpleNamespace(
            amount=Decimal("12.00"),
            currency="usd",
            carrier="UPS",
            service="Ground",
            rate_id="rate_2",
            raw_ref="shp_2",
        )
        with patch("orders.views.quote_shipping_for_order", return_value=quote_first):
            self.client.post(
                reverse("customers:order_new"),
                {
                    "action": "verify",
                    "shipping_address": str(self.address.id),
                    "product_id": str(self.product.id),
                    f"quantity_{self.product.id}": "2",
                },
            )
        session_drafts = self.client.session.get("customer_order_drafts", {})
        draft_token = list(session_drafts.keys())[0]

        with patch("orders.views.quote_shipping_for_order", return_value=quote_second):
            response = self.client.post(
                reverse("customers:order_new"),
                {"action": "confirm", "draft_token": draft_token},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shipping quote changed")
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)

    def test_verify_quote_failure_blocks_progress(self):
        from fulfillment.shipping_quote import ShippingQuoteError

        self.client.login(username="customer1", password="pass1234")
        with patch("orders.views.quote_shipping_for_order", side_effect=ShippingQuoteError("No rates")):
            response = self.client.post(
                reverse("customers:order_new"),
                {
                    "action": "verify",
                    "shipping_address": str(self.address.id),
                    "product_id": str(self.product.id),
                    f"quantity_{self.product.id}": "2",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shipping quote failed")
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)


@override_settings(EASYPOST_ENABLED=False, EASYPOST_API_KEY="")
class AdminOrderWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = Customer.objects.create(name="Ops Customer", payment_terms="NET_30")
        self.address = ShippingAddress.objects.create(
            customer=self.customer,
            label="Main",
            line1="500 State",
            city="Austin",
            state="TX",
            postal_code="78701",
        )
        self.product = Product.objects.create(sku="SKU-OPS", name="Ops Product")
        self.order = Order.objects.create(
            customer=self.customer,
            shipping_address=self.address,
            status=OrderStatus.SUBMITTED,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price=Decimal("10.00"),
            extended_price=Decimal("10.00"),
        )
        self.order.recalculate_totals()
        user_model = get_user_model()
        self.ops = user_model.objects.create_user(
            username="ops-workflow",
            password="pass1234",
            is_ops_user=True,
        )

    def test_order_detail_shows_only_allowed_actions_for_status(self):
        self.client.login(username="ops-workflow", password="pass1234")
        response = self.client.get(reverse("admin_portal:order_detail", args=[self.order.id]))
        self.assertContains(response, "Under Review")
        self.assertContains(response, "Cancel")
        self.assertNotContains(response, "Shipped")

    def test_invalid_action_does_not_change_status_or_create_shipment(self):
        self.client.login(username="ops-workflow", password="pass1234")
        response = self.client.post(
            reverse("admin_portal:order_action", args=[self.order.id]),
            {"action": "ship_full", "carrier": "UPS", "tracking_number": "1Z"},
            follow=True,
        )
        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, OrderStatus.SUBMITTED)
        self.assertEqual(Shipment.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_archive_hides_order_from_list_by_default(self):
        self.client.login(username="ops-workflow", password="pass1234")
        self.client.post(reverse("admin_portal:order_archive", args=[self.order.id]))

        response = self.client.get(reverse("admin_portal:orders"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f"#{self.order.id}")

        response = self.client.get(reverse("admin_portal:orders") + "?archived=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"#{self.order.id}")

    def test_happy_path_to_shipped_creates_shipment_and_invoice(self):
        self.client.login(username="ops-workflow", password="pass1234")
        actions = ["under_review", "approve", "release", "picking", "packed", "ship_full"]
        for action in actions:
            self.client.post(
                reverse("admin_portal:order_action", args=[self.order.id]),
                {"action": action, "carrier": "UPS", "tracking_number": "1Z123"},
            )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.SHIPPED)
        self.assertEqual(Shipment.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        invoice = Invoice.objects.get(order=self.order, invoice_kind=Invoice.InvoiceKind.PRIMARY)
        self.assertEqual(invoice.shipping_total, Decimal("0.00"))

    def test_approve_with_shipping_override_is_used(self):
        self.client.login(username="ops-workflow", password="pass1234")
        self.client.post(reverse("admin_portal:order_action", args=[self.order.id]), {"action": "under_review"})
        self.client.post(
            reverse("admin_portal:order_action", args=[self.order.id]),
            {"action": "approve", "shipping_override": "12.34"},
        )
        invoice = Invoice.objects.get(order=self.order, invoice_kind=Invoice.InvoiceKind.PRIMARY)
        self.assertEqual(invoice.shipping_total, Decimal("12.34"))
        self.assertEqual(invoice.shipping_input_source, "MANUAL_OVERRIDE")

    @override_settings(EASYPOST_ENABLED=True, EASYPOST_API_KEY="EZTK_TEST")
    def test_ship_creates_adjustment_invoice_when_delta_exists(self):
        self.client.login(username="ops-workflow", password="pass1234")
        self.client.post(reverse("admin_portal:order_action", args=[self.order.id]), {"action": "under_review"})

        quote_approve = SimpleNamespace(
            amount=Decimal("5.00"),
            currency="usd",
            carrier="UPS",
            service="Ground",
            rate_id="rate_approve",
        )
        quote_ship = SimpleNamespace(
            amount=Decimal("9.00"),
            currency="usd",
            carrier="UPS",
            service="Ground",
            rate_id="rate_ship",
        )

        with patch("invoicing.services.quote_shipping_for_order", return_value=quote_approve):
            self.client.post(reverse("admin_portal:order_action", args=[self.order.id]), {"action": "approve"})

        for action in ["release", "picking", "packed"]:
            self.client.post(reverse("admin_portal:order_action", args=[self.order.id]), {"action": action})

        with patch("invoicing.services.quote_shipping_for_order", return_value=quote_ship):
            self.client.post(
                reverse("admin_portal:order_action", args=[self.order.id]),
                {"action": "ship_full", "carrier": "UPS", "tracking_number": "1Z123"},
            )
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 2)
        adjustment = Invoice.objects.filter(order=self.order).exclude(invoice_kind=Invoice.InvoiceKind.PRIMARY).first()
        self.assertIsNotNone(adjustment)
