from django.test import TestCase

from products.models import Product


class ProductSkuTests(TestCase):
    def test_auto_sku_starts_from_seed(self):
        product = Product.objects.create(name="Fish Oil", case_quantity=1, active=True, sku="")
        self.assertEqual(product.sku, "PVB-100001")

    def test_auto_sku_increments(self):
        first = Product.objects.create(name="A", case_quantity=1, active=True, sku="")
        second = Product.objects.create(name="B", case_quantity=1, active=True, sku="")
        self.assertEqual(first.sku, "PVB-100001")
        self.assertEqual(second.sku, "PVB-100002")
