from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from customers.models import Customer


class CustomerAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        user_model = get_user_model()
        self.customer = Customer.objects.create(name="North", payment_terms="NET_30")
        self.customer_user = user_model.objects.create_user(
            username="cust",
            password="pass1234",
            is_customer_user=True,
            customer=self.customer,
        )
        self.ops_user = user_model.objects.create_user(
            username="ops",
            password="pass1234",
            is_ops_user=True,
        )

    def test_customer_user_can_load_dashboard(self):
        self.client.login(username="cust", password="pass1234")
        response = self.client.get(reverse("customers:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_customer_user_cannot_open_admin_portal(self):
        self.client.login(username="cust", password="pass1234")
        response = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_ops_user_can_open_admin_portal(self):
        self.client.login(username="ops", password="pass1234")
        response = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(response.status_code, 200)
