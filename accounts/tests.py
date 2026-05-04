from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from customers.models import Customer


class CustomerUserAdminPortalTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.ops = user_model.objects.create_user(
            username="ops1",
            password="pass1234",
            is_ops_user=True,
        )
        self.customer = Customer.objects.create(name="Acme", payment_terms="NET_30")

    def test_ops_can_create_customer_user(self):
        self.client.login(username="ops1", password="pass1234")
        response = self.client.post(
            reverse("admin_portal:customer_user_create"),
            {
                "username": "acme_user_1",
                "email": "acme1@example.com",
                "first_name": "Acme",
                "last_name": "User",
                "customer": self.customer.id,
                "is_active": "on",
                "password1": "pass12345",
                "password2": "pass12345",
            },
        )
        self.assertEqual(response.status_code, 302)
        user_model = get_user_model()
        created = user_model.objects.get(username="acme_user_1")
        self.assertTrue(created.is_customer_user)
        self.assertEqual(created.customer_id, self.customer.id)
