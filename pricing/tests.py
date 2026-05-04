from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from customers.models import Customer
from pricing.models import CustomerPrice
from pricing.services import get_active_customer_price
from products.models import Product


class CustomerPriceTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Acme", payment_terms="NET_30")
        self.product = Product.objects.create(sku="SKU-1", name="Fish Oil")

    def test_overlap_is_blocked(self):
        CustomerPrice.objects.create(
            customer=self.customer,
            product=self.product,
            unit_price=Decimal("10.00"),
            minimum_quantity=1,
            effective_date=date(2026, 1, 1),
            expiration_date=date(2026, 1, 31),
        )
        price = CustomerPrice(
            customer=self.customer,
            product=self.product,
            unit_price=Decimal("11.00"),
            minimum_quantity=1,
            effective_date=date(2026, 1, 15),
            expiration_date=date(2026, 2, 1),
        )
        with self.assertRaises(ValidationError):
            price.full_clean()

    def test_resolves_active_price(self):
        CustomerPrice.objects.create(
            customer=self.customer,
            product=self.product,
            unit_price=Decimal("10.00"),
            minimum_quantity=1,
            effective_date=date(2026, 1, 1),
            expiration_date=date(2026, 1, 31),
        )
        CustomerPrice.objects.create(
            customer=self.customer,
            product=self.product,
            unit_price=Decimal("9.50"),
            minimum_quantity=2,
            effective_date=date(2026, 2, 1),
            expiration_date=None,
        )
        active = get_active_customer_price(
            self.customer, self.product, as_of=date(2026, 2, 10)
        )
        self.assertEqual(active.unit_price, Decimal("9.50"))
