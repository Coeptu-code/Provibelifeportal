from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from customers.models import Customer
from invoicing.models import Invoice, InvoiceStatus
from orders.models import Order, OrderStatus
from payments.models import Payment, ShopifyWebhookEvent, StripeWebhookEvent
from payments.services import process_stripe_event
from shopify_integration.services import process_shopify_webhook


class StripeWebhookTests(TestCase):
    def setUp(self):
        customer = Customer.objects.create(name="Webhook Co", payment_terms="NET_30")
        order = Order.objects.create(customer=customer, status=OrderStatus.SHIPPED)
        self.invoice = Invoice.objects.create(
            order=order,
            customer=customer,
            invoice_number="INV-1",
            subtotal=Decimal("50.00"),
            shipping_total=Decimal("0.00"),
            tax_total=Decimal("0.00"),
            total=Decimal("50.00"),
            status=InvoiceStatus.SENT,
            stripe_invoice_id="in_abc123",
        )

    def test_invoice_paid_updates_status_and_is_idempotent(self):
        event = {
            "id": "evt_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "id": "in_abc123",
                    "status": "paid",
                    "amount_paid": 5000,
                    "amount_remaining": 0,
                }
            },
        }
        first = process_stripe_event(event)
        second = process_stripe_event(event)
        self.invoice.refresh_from_db()
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)
        self.assertIsNotNone(self.invoice.paid_at)
        self.assertEqual(StripeWebhookEvent.objects.count(), 1)


class ShopifyWebhookTests(TestCase):
    def setUp(self):
        customer = Customer.objects.create(name="Shopify Co", payment_terms="NET_30")
        order = Order.objects.create(customer=customer, status=OrderStatus.APPROVED)
        self.invoice = Invoice.objects.create(
            order=order,
            customer=customer,
            invoice_number="INV-SHOP",
            subtotal=Decimal("75.00"),
            shipping_total=Decimal("5.00"),
            tax_total=Decimal("0.00"),
            total=Decimal("80.00"),
            status=InvoiceStatus.SENT,
        )

    def test_orders_paid_updates_status_and_creates_payment(self):
        payload = {
            "id": 2001,
            "name": "#1001",
            "current_total_price": "80.00",
            "note_attributes": [
                {"name": "local_invoice_id", "value": str(self.invoice.id)},
                {"name": "local_order_id", "value": str(self.invoice.order_id)},
            ],
        }
        first = process_shopify_webhook("orders/paid", payload, "shop_evt_1", "store.myshopify.com")
        second = process_shopify_webhook("orders/paid", payload, "shop_evt_1", "store.myshopify.com")
        self.invoice.refresh_from_db()
        self.invoice.order.refresh_from_db()
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)
        self.assertEqual(self.invoice.order.shopify_order_id, "2001")
        self.assertEqual(Payment.objects.filter(invoice=self.invoice).count(), 1)
        self.assertEqual(ShopifyWebhookEvent.objects.count(), 1)

    def test_orders_cancelled_voids_invoice(self):
        payload = {
            "id": 2002,
            "note_attributes": [
                {"name": "local_invoice_id", "value": str(self.invoice.id)},
                {"name": "local_order_id", "value": str(self.invoice.order_id)},
            ],
        }
        process_shopify_webhook("orders/cancelled", payload, "shop_evt_2", "store.myshopify.com")
        self.invoice.refresh_from_db()
        self.invoice.order.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.VOID)
        self.assertEqual(self.invoice.order.status, OrderStatus.CANCELLED)


@override_settings(
    SHOPIFY_CLIENT_ID="client-id",
    SHOPIFY_CLIENT_SECRET="client-secret",
    SHOPIFY_SHOP="store.myshopify.com",
    SHOPIFY_REDIRECT_URI="https://example.com/webhooks/auth/shopify/callback/",
    SHOPIFY_APP_SCOPES=["read_orders"],
)
class ShopifyOAuthViewTests(TestCase):
    def test_install_redirects_to_shopify_authorize(self):
        response = self.client.get(reverse("shopify_oauth_install"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("store.myshopify.com/admin/oauth/authorize", response["Location"])

    def test_callback_rejects_invalid_hmac(self):
        response = self.client.get(
            reverse("shopify_oauth_callback"),
            {"shop": "store.myshopify.com", "code": "abc", "state": "bad", "hmac": "bad"},
        )
        self.assertEqual(response.status_code, 400)
