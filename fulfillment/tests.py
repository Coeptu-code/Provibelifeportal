from django.test import TestCase
from decimal import Decimal

from customers.models import Customer, ShippingAddress
from fulfillment.shipping_quote import _build_parcels, _select_rate
from orders.models import Order, OrderItem
from products.models import Product


class ShippingQuoteHelpersTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Ship Co", payment_terms="NET_30")
        self.address = ShippingAddress.objects.create(
            customer=self.customer,
            label="Main",
            line1="123 Main",
            city="Austin",
            state="TX",
            postal_code="78701",
        )
        self.product = Product.objects.create(
            sku="SKU-SHIP",
            name="Ship Product",
            shipping_weight=Decimal("1.00"),
            shipping_weight_unit="lb",
            shipping_length=Decimal("10.00"),
            shipping_width=Decimal("5.00"),
            shipping_height=Decimal("4.00"),
            shipping_dimension_unit="in",
            active=True,
        )
        self.order = Order.objects.create(customer=self.customer, shipping_address=self.address)
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("5.00"),
            extended_price=Decimal("10.00"),
        )

    def test_build_parcels_from_quantity(self):
        parcels = _build_parcels(self.order)
        self.assertEqual(len(parcels), 2)
        self.assertEqual(parcels[0]["weight"], "16.00")

    def test_select_rate_prefers_carrier_then_cheapest(self):
        rates = [
            {"carrier": "USPS", "service": "Ground", "rate": "12.00", "id": "r1"},
            {"carrier": "UPS", "service": "Ground", "rate": "14.00", "id": "r2"},
            {"carrier": "UPS", "service": "Express", "rate": "11.00", "id": "r3"},
        ]
        selected = _select_rate(rates, "UPS")
        self.assertEqual(selected["id"], "r3")

    def test_select_rate_falls_back_to_cheapest(self):
        rates = [
            {"carrier": "USPS", "service": "Ground", "rate": "12.00", "id": "r1"},
            {"carrier": "FEDEX", "service": "Express", "rate": "9.00", "id": "r2"},
        ]
        selected = _select_rate(rates, "UPS")
        self.assertEqual(selected["id"], "r2")
