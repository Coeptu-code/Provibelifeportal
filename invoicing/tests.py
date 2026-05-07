from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from customers.models import Customer, ShippingAddress
from invoicing.models import Invoice, InvoiceStatus
from invoicing.services import create_invoice_for_order, create_shipping_adjustment_invoice, send_invoice_to_provider
from orders.models import Order, OrderItem, OrderStatus
from products.models import Product


class InvoiceGenerationTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Central", payment_terms="NET_30")
        self.address = ShippingAddress.objects.create(
            customer=self.customer,
            label="Main",
            line1="1 Center",
            city="Houston",
            state="TX",
            postal_code="77001",
        )
        self.product = Product.objects.create(sku="SKU-3", name="C")
        self.order = Order.objects.create(
            customer=self.customer,
            shipping_address=self.address,
            status=OrderStatus.APPROVED,
            subtotal=Decimal("120.00"),
            total=Decimal("120.00"),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=10,
            unit_price=Decimal("12.00"),
            extended_price=Decimal("120.00"),
        )

    def test_due_date_from_net_terms(self):
        invoice = create_invoice_for_order(self.order)
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
        self.assertGreaterEqual((invoice.due_date - date.today()).days, 29)

    def test_create_invoice_requires_shipped_status(self):
        self.order.status = OrderStatus.PACKED
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValueError):
            create_invoice_for_order(self.order)

    def test_shipping_total_is_included_in_invoice_total(self):
        quote = type(
            "Quote",
            (),
            {
                "amount": Decimal("18.25"),
                "currency": "usd",
                "carrier": "UPS",
                "service": "Ground",
                "rate_id": "rate_abc",
            },
        )()
        invoice = create_invoice_for_order(
            self.order,
            shipping_total=Decimal("18.25"),
            tax_total=Decimal("1.75"),
            shipping_quote=quote,
        )
        self.assertEqual(invoice.shipping_total, Decimal("18.25"))
        self.assertEqual(invoice.tax_total, Decimal("1.75"))
        self.assertEqual(invoice.total, Decimal("140.00"))
        self.assertEqual(invoice.shipping_carrier, "UPS")
        self.assertEqual(invoice.shipping_quote_status, "SUCCESS")
        self.assertTrue(bool(invoice.pdf_file))

    @override_settings(SHOPIFY_ENABLED=False, STRIPE_INVOICING_ENABLED=False)
    def test_shipping_adjustment_invoice_allows_second_invoice_for_same_order(self):
        primary = create_invoice_for_order(self.order, shipping_total=Decimal("5.00"))
        adjustment = create_shipping_adjustment_invoice(self.order, primary, Decimal("-2.50"))
        self.assertIsNotNone(adjustment)
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 2)
        self.assertEqual(adjustment.invoice_kind, Invoice.InvoiceKind.ADJUSTMENT_CREDIT)
        self.assertEqual(adjustment.total, Decimal("-2.50"))

    @override_settings(SHOPIFY_ENABLED=True)
    def test_send_invoice_to_provider_uses_shopify_sender(self):
        invoice = create_invoice_for_order(self.order, shipping_total=Decimal("5.00"))
        with patch("invoicing.services.send_invoice_to_shopify") as mocked_sender:
            mocked_sender.return_value = invoice
            send_invoice_to_provider(invoice)
        mocked_sender.assert_called_once_with(invoice)
