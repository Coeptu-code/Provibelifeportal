import requests
from django.conf import settings
from django.template.loader import render_to_string


def send_email(to: str, subject: str, html: str) -> None:
    if not settings.RESEND_ENABLED:
        print(f"[EMAIL] To: {to} | Subject: {subject}")
        return
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={"from": settings.EMAIL_FROM, "to": [to], "subject": subject, "html": html},
            timeout=10,
        )
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {to}: {e}")


def send_invitation_email(invitation, accept_url: str) -> None:
    subject = f"You're invited to {invitation.customer.name}"
    html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <h2>Welcome to Pro Vibe Life Portal</h2>
      <p>You've been invited by <strong>{invitation.invited_by.get_full_name or invitation.invited_by.username}</strong> to manage orders for <strong>{invitation.customer.name}</strong>.</p>
      <p><a href="{accept_url}" style="display: inline-block; background-color: #d4a574; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Create Your Account</a></p>
      <p>This link expires in 7 days.</p>
    </body></html>
    """
    send_email(invitation.email, subject, html)


def send_password_reset_email(user, reset_url: str) -> None:
    subject = "Reset your Pro Vibe Life Portal password"
    html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <h2>Password Reset Request</h2>
      <p>Click the link below to reset your password:</p>
      <p><a href="{reset_url}" style="display: inline-block; background-color: #d4a574; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Reset Password</a></p>
      <p>This link expires in 24 hours. If you didn't request a password reset, please ignore this email.</p>
    </body></html>
    """
    send_email(user.email, subject, html)


def send_retailer_shilajit_info_email(*, to: str, account_creation_url: str) -> None:
    subject = "Pro Vibe Life Shilajit Retailer Information"
    html = render_to_string(
        "emails/retailer_shilajit_info.html",
        {"account_creation_url": account_creation_url},
    )
    send_email(to, subject, html)


MOBILE_APP_DOWNLOAD_URL = "https://portal.provibelife.com/retailer-app/mobile"


def send_retailer_vitali_t_info_email(*, to: str, account_creation_url: str) -> None:
    subject = "Pro Vibe Life Vitali-T — Retailer Product Information"
    html = render_to_string(
        "emails/retailer_vitali_t_info.html",
        {"account_creation_url": account_creation_url},
    )
    send_email(to, subject, html)


def send_retailer_app_invite_email(*, to: str, account_creation_url: str) -> None:
    subject = "You're invited — Pro Vibe Life Retail Portal + Mobile App"
    html = render_to_string(
        "emails/retailer_app_invite.html",
        {
            "account_creation_url": account_creation_url,
            "mobile_app_download_url": MOBILE_APP_DOWNLOAD_URL,
        },
    )
    send_email(to, subject, html)
