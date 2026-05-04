from decimal import Decimal

from django.test import TestCase

from customers.models import Customer
from invoicing.models import Invoice, InvoiceStatus
from orders.models import Order, OrderStatus
from payments.models import StripeWebhookEvent
from payments.services import process_stripe_event


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
