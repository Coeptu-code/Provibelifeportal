from unittest.mock import patch

from decimal import Decimal

from django.test import TestCase, override_settings

from customers.models import Customer, ShippingAddress
from fulfillment.shipping_quote import (
    _build_parcels,
    _select_rate,
    build_shopify_carrier_rates,
    quote_shipping_for_order,
)
from orders.models import Order, OrderItem
from products.models import Product
from shopify_integration.services import ShopifySyncError


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
            shopify_variant_id="101",
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
        self.assertEqual(parcels[0]["weight_oz"], Decimal("16.00"))

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

    @override_settings(
        SHIPPING_PROVIDER="shopify",
        SHOPIFY_ENABLED=True,
        SHOPIFY_DEFAULT_CURRENCY="usd",
        SHIP_FROM_NAME="Warehouse",
        SHIP_FROM_STREET1="1 Dock",
        SHIP_FROM_CITY="Austin",
        SHIP_FROM_STATE="TX",
        SHIP_FROM_ZIP="78701",
    )
    def test_shopify_quote_uses_local_rate_engine(self):
        quote = quote_shipping_for_order(self.order)
        self.assertGreater(quote.amount, Decimal("0.00"))
        self.assertEqual(quote.currency, "usd")
        self.assertIn("shopify-rate", quote.rate_id)

    @override_settings(
        SHIPPING_PROVIDER="shopify",
        SHOPIFY_ENABLED=True,
        SHIP_FROM_NAME="Warehouse",
        SHIP_FROM_STREET1="1 Dock",
        SHIP_FROM_CITY="Austin",
        SHIP_FROM_STATE="TX",
        SHIP_FROM_ZIP="78701",
    )
    def test_shopify_quote_fails_when_sku_cannot_be_resolved(self):
        self.product.shopify_variant_id = ""
        self.product.save(update_fields=["shopify_variant_id"])
        with patch(
            "fulfillment.shipping_quote.ensure_shopify_product_mapping",
            side_effect=ShopifySyncError("SKU SKU-SHIP could not be resolved in Shopify."),
        ):
            with self.assertRaisesMessage(Exception, "could not be resolved in Shopify"):
                quote_shipping_for_order(self.order)

    def test_build_shopify_carrier_rates_from_callback_payload(self):
        rates = build_shopify_carrier_rates(
            {
                "rate": {
                    "destination": {"province": "TX", "country": "US"},
                    "items": [
                        {"quantity": 2, "grams": 454},
                    ],
                }
            }
        )
        self.assertEqual(len(rates), 1)
        self.assertEqual(rates[0]["currency"], "USD")
        self.assertTrue(int(rates[0]["total_price"]) > 0)
