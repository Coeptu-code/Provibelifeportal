from datetime import timedelta
import os
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from customers.models import Customer
from accounts.models import (
    CustomerInvitation,
    RetailerLead,
    RetailerAccountCreationToken,
    RetailerMarketingPageToken,
)


class CustomerUserAdminPortalTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.ops = user_model.objects.create_user(
            username="ops1",
            password="pass1234",
            is_ops_user=True,
        )
        self.customer = Customer.objects.create(name="Acme", payment_terms="NET_30")

    def test_ops_can_send_customer_user_invitation(self):
        self.client.login(username="ops1", password="pass1234")
        with patch("accounts.email_service.send_email"):
            response = self.client.post(
            reverse("admin_portal:customer_user_create"),
            {
                "email": "acme1@example.com",
                "customer": self.customer.id,
            },
            )
        self.assertEqual(response.status_code, 302)
        invitation = CustomerInvitation.objects.get(email="acme1@example.com", customer=self.customer)
        self.assertTrue(invitation.is_valid)

    def test_invitation_accept_page_handles_missing_inviter(self):
        invitation = CustomerInvitation.objects.create(
            email="newuser@example.com",
            customer=self.customer,
            invited_by=None,
        )
        response = self.client.get(reverse("invitation_accept", kwargs={"token": invitation.token}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Your Account")


@override_settings(SITE_URL="https://portal.provibelife.com")
class MarketingEmailTokenFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="admin1",
            password="pass1234",
            role=user_model.Role.ADMIN,
            is_active=True,
        )

    def test_marketing_email_send_renders_account_creation_url(self):
        self.client.login(username="admin1", password="pass1234")
        captured = {}

        def _capture_send_email(to, subject, html):
            captured["to"] = to
            captured["subject"] = subject
            captured["html"] = html

        with patch("accounts.email_service.send_email", side_effect=_capture_send_email):
            resp = self.client.post(
                reverse("admin_portal:marketing_email_shilajit"),
                {"email": "healthstore@example.com", "store_name": "Health Store", "phone": "+1-555-1212"},
            )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(captured["to"], "healthstore@example.com")
        self.assertIn("Shilajit Retailer Information", captured["subject"])
        self.assertIn("https://portal.provibelife.com/retailer/create-account/?token=", captured["html"])
        self.assertNotIn("{{ account_creation_url }}", captured["html"])

        lead = RetailerLead.objects.get(email="healthstore@example.com")
        self.assertEqual(lead.phone, "+1-555-1212")
        token = RetailerAccountCreationToken.objects.get(lead=lead)
        self.assertTrue(str(token.token) in captured["html"])

    def test_tokens_are_unique_per_recipient(self):
        self.client.login(username="admin1", password="pass1234")
        with patch("accounts.email_service.send_email"):
            self.client.post(reverse("admin_portal:marketing_email_shilajit"), {"email": "a@example.com"})
            self.client.post(reverse("admin_portal:marketing_email_shilajit"), {"email": "b@example.com"})

        token_a = RetailerAccountCreationToken.objects.get(lead__email="a@example.com").token
        token_b = RetailerAccountCreationToken.objects.get(lead__email="b@example.com").token
        self.assertNotEqual(token_a, token_b)

    def test_invalid_token_rejected(self):
        resp = self.client.get("/retailer/create-account/?token=not-a-uuid")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid or missing account creation link.")

    def test_expired_token_rejected(self):
        lead = RetailerLead.objects.create(email="expired@example.com", created_by=self.admin)
        token = RetailerAccountCreationToken.objects.create(
            lead=lead,
            created_by=self.admin,
            expires_at=timezone.now() - timedelta(days=1),
        )
        resp = self.client.get(f"/retailer/create-account/?token={token.token}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "expired or been used")

    def test_valid_token_shows_form(self):
        lead = RetailerLead.objects.create(email="valid@example.com", created_by=self.admin)
        token = RetailerAccountCreationToken.objects.create(lead=lead, created_by=self.admin)
        resp = self.client.get(f"/retailer/create-account/?token={token.token}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Create Retailer Account")
        self.assertContains(resp, 'name="username"')

    def test_valid_token_creates_customer_and_user_and_marks_used(self):
        lead = RetailerLead.objects.create(email="signup@example.com", store_name="Zen Health", created_by=self.admin)
        token = RetailerAccountCreationToken.objects.create(lead=lead, created_by=self.admin)

        resp = self.client.post(
            f"/retailer/create-account/?token={token.token}",
            {
                "store_name": "Zen Health",
                "username": "zenhealth",
                "first_name": "Zed",
                "last_name": "Owner",
                "password1": "pass12345",
                "password2": "pass12345",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("customers:dashboard"))

        user_model = get_user_model()
        user = user_model.objects.get(username="zenhealth")
        self.assertEqual(user.email, "signup@example.com")
        self.assertTrue(user.is_customer_user)
        self.assertIsNotNone(user.customer_id)

        created_customer = Customer.objects.get(id=user.customer_id)
        self.assertTrue(created_customer.is_active)

        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

        lead.refresh_from_db()
        self.assertEqual(lead.created_customer_id, created_customer.id)

        resp2 = self.client.get(f"/retailer/create-account/?token={token.token}")
        self.assertContains(resp2, "expired or been used")


@override_settings(SITE_URL="https://portal.provibelife.com")
class AbsoluteLinkTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.ops = user_model.objects.create_user(
            username="ops2",
            password="pass1234",
            role=user_model.Role.SALES_REP,
            is_active=True,
        )
        self.customer = Customer.objects.create(name="Bravo", payment_terms="NET_30")

    def test_invitation_email_uses_absolute_domain(self):
        self.client.login(username="ops2", password="pass1234")
        captured = {}

        def _capture_send_email(to, subject, html):
            captured["to"] = to
            captured["subject"] = subject
            captured["html"] = html

        with patch("accounts.email_service.send_email", side_effect=_capture_send_email):
            response = self.client.post(
                reverse("admin_portal:customer_user_create"),
                {"email": "bravo@example.com", "customer": self.customer.id},
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("https://portal.provibelife.com/accounts/invite/", captured["html"])

    def test_password_reset_email_uses_absolute_domain(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="pass1234",
            role=user_model.Role.CUSTOMER_USER,
            customer=self.customer,
            is_active=True,
        )
        captured = {}

        def _capture_send_email(to, subject, html):
            captured["to"] = to
            captured["subject"] = subject
            captured["html"] = html

        with patch("accounts.email_service.send_email", side_effect=_capture_send_email):
            response = self.client.post(reverse("password_reset"), {"email": "reset@example.com"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("https://portal.provibelife.com/accounts/reset/", captured["html"])


@override_settings(SITE_URL="https://portal.provibelife.com")
class FreeSampleTokenFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="admin_free_sample",
            password="pass1234",
            role=user_model.Role.ADMIN,
            is_active=True,
        )

    def test_tokenized_page_click_tracking(self):
        lead = RetailerLead.objects.create(
            email="lead@example.com",
            phone="+1-222-333-4444",
            created_by=self.admin,
        )
        token = RetailerMarketingPageToken.objects.create(
            lead=lead,
            created_by=self.admin,
        )
        resp = self.client.get(f"/pages/free-sample/?token={token.token}")
        self.assertEqual(resp.status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.click_count, 1)
        self.assertIsNotNone(token.last_clicked_at)

    def test_invalid_free_sample_token_returns_404(self):
        resp = self.client.get("/pages/free-sample/?token=invalid")
        self.assertEqual(resp.status_code, 404)

    def test_click_report_contains_phone(self):
        lead = RetailerLead.objects.create(
            email="phonelead@example.com",
            phone="+1-999-888-7777",
            created_by=self.admin,
        )
        token = RetailerMarketingPageToken.objects.create(
            lead=lead,
            created_by=self.admin,
            source="test-campaign",
        )
        self.client.get(f"/pages/free-sample/?token={token.token}")

        self.client.login(username="admin_free_sample", password="pass1234")
        resp = self.client.get(reverse("admin_portal:marketing_free_sample_clicks"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "phonelead@example.com")
        self.assertContains(resp, "+1-999-888-7777")

    def test_link_builder_reuses_active_token_when_requested(self):
        self.client.login(username="admin_free_sample", password="pass1234")
        payload = {
            "email": "reuse@example.com",
            "store_name": "Reuse Store",
            "source": "may-2026",
            "reuse_active": "1",
        }
        first = self.client.post(reverse("admin_portal:marketing_free_sample_links"), payload)
        self.assertEqual(first.status_code, 200)
        second = self.client.post(reverse("admin_portal:marketing_free_sample_links"), payload)
        self.assertEqual(second.status_code, 200)

        lead = RetailerLead.objects.get(email="reuse@example.com")
        tokens = RetailerMarketingPageToken.objects.filter(
            lead=lead,
            source="may-2026",
            page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE,
        )
        self.assertEqual(tokens.count(), 1)
        self.assertContains(second, "Reused Active Token")

    def test_click_report_filters_clicked_yes(self):
        lead_clicked = RetailerLead.objects.create(email="clicked@example.com", created_by=self.admin)
        lead_not_clicked = RetailerLead.objects.create(email="notclicked@example.com", created_by=self.admin)
        token_clicked = RetailerMarketingPageToken.objects.create(lead=lead_clicked, created_by=self.admin)
        RetailerMarketingPageToken.objects.create(lead=lead_not_clicked, created_by=self.admin)

        self.client.get(f"/pages/free-sample/?token={token_clicked.token}")
        self.client.login(username="admin_free_sample", password="pass1234")
        resp = self.client.get(reverse("admin_portal:marketing_free_sample_clicks"), {"clicked": "yes"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "clicked@example.com")
        self.assertNotContains(resp, "notclicked@example.com")

    def test_click_report_groups_emails_by_campaign_source(self):
        lead_a = RetailerLead.objects.create(email="groupa@example.com", created_by=self.admin)
        lead_b = RetailerLead.objects.create(email="groupb@example.com", created_by=self.admin)
        RetailerMarketingPageToken.objects.create(lead=lead_a, created_by=self.admin, source="campaign-alpha")
        RetailerMarketingPageToken.objects.create(lead=lead_b, created_by=self.admin, source="campaign-alpha")

        self.client.login(username="admin_free_sample", password="pass1234")
        resp = self.client.get(reverse("admin_portal:marketing_free_sample_clicks"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Campaign Groups")
        self.assertContains(resp, "campaign-alpha")
        self.assertContains(resp, "groupa@example.com")
        self.assertContains(resp, "groupb@example.com")

    def test_click_report_can_reset_free_sample_click_and_lead_data(self):
        lead = RetailerLead.objects.create(email="reset-me@example.com", created_by=self.admin)
        RetailerMarketingPageToken.objects.create(lead=lead, created_by=self.admin, source="campaign-reset")

        self.client.login(username="admin_free_sample", password="pass1234")
        resp = self.client.post(
            reverse("admin_portal:marketing_free_sample_clicks"),
            {"action": "reset_free_sample_data"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Free-sample click/lead system reset")
        self.assertEqual(RetailerMarketingPageToken.objects.count(), 0)
        self.assertEqual(RetailerLead.objects.filter(email="reset-me@example.com").count(), 0)

    def test_tokenized_page_click_tracking_with_path_route(self):
        lead = RetailerLead.objects.create(email="pathlead@example.com", created_by=self.admin)
        token = RetailerMarketingPageToken.objects.create(lead=lead, created_by=self.admin)
        resp = self.client.get(f"/pages/free-sample/{token.token}/")
        self.assertEqual(resp.status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.click_count, 1)

    def test_mailer_bulk_create_api_creates_tokens(self):
        with patch.dict(os.environ, {"PORTAL_MAILER_API_KEY": "test-key"}):
            resp = self.client.post(
                "/api/mailer/free-sample-tokens/bulk-create/",
                data={
                    "source": "campaign-1",
                    "leads": [
                        {"email": "bulk1@example.com", "store_name": "Bulk One"},
                        {"email": "bulk2@example.com", "store_name": "Bulk Two", "is_test": True},
                    ],
                },
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer test-key",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["created_count"], 2)
        self.assertEqual(RetailerLead.objects.filter(email="bulk1@example.com").count(), 1)
        self.assertEqual(RetailerMarketingPageToken.objects.filter(lead__email="bulk2@example.com", is_test=True).count(), 1)

    def test_mailer_token_status_api_returns_clicked_state(self):
        lead = RetailerLead.objects.create(email="status@example.com", created_by=self.admin)
        token = RetailerMarketingPageToken.objects.create(lead=lead, created_by=self.admin, is_test=True)
        self.client.get(f"/pages/free-sample/?token={token.token}")
        with patch.dict(os.environ, {"PORTAL_MAILER_API_KEY": "test-key"}):
            resp = self.client.get(
                f"/api/mailer/free-sample-tokens/{token.token}/status/",
                HTTP_AUTHORIZATION="Bearer test-key",
            )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload["clicked"])
        self.assertTrue(payload["is_test"])

    def test_bulk_token_generator_download_exports_email_and_token_only(self):
        self.client.login(username="admin_free_sample", password="pass1234")
        generate_resp = self.client.post(
            reverse("admin_portal:marketing_free_sample_token_generator"),
            {
                "action": "generate",
                "bulk_text": "email\nbulk-export@example.com\n",
                "source": "csv-export-test",
            },
        )
        self.assertEqual(generate_resp.status_code, 200)

        download_resp = self.client.post(
            reverse("admin_portal:marketing_free_sample_token_generator"),
            {"action": "download"},
        )
        self.assertEqual(download_resp.status_code, 200)
        self.assertEqual(download_resp["Content-Type"], "text/csv")

        csv_lines = download_resp.content.decode("utf-8").strip().splitlines()
        self.assertGreaterEqual(len(csv_lines), 2)
        self.assertEqual(csv_lines[0], "email,token")
        self.assertIn("bulk-export@example.com,", csv_lines[1])
