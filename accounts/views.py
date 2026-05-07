from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
import uuid

from accounts.decorators import admin_required, customer_required, sales_required
from accounts.activity import log_activity
from accounts.email_service import (
    send_invitation_email,
    send_retailer_shilajit_info_email, send_retailer_app_invite_email,
    send_retailer_vitali_t_info_email, MOBILE_APP_DOWNLOAD_URL,
)
from accounts.url_utils import absolute_view_url
from accounts.forms import (
    AcceptInvitationForm, CustomPasswordResetForm, CustomerUserCreateForm, CustomerUserUpdateForm,
    InternalUserCreateForm, InternalUserUpdateForm, SendInvitationForm, MarketingShilajitEmailForm,
    RetailerAccountCreateForm,
)
from accounts.models import CustomerInvitation, RetailerLead, RetailerAccountCreationToken
from customers.models import Customer

User = get_user_model()

@login_required
def root_redirect(request):
    if request.user.is_customer_user:
        return redirect("customers:dashboard")
    if request.user.is_ops_user or request.user.is_staff or request.user.is_superuser:
        return redirect("admin_portal:dashboard")
    return render(request, "registration/no_role.html")


@sales_required
def admin_send_invitation(request):
    customer_id = request.GET.get("customer")
    if request.method == "POST":
        form = SendInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            customer = form.cleaned_data["customer"]

            invitation = CustomerInvitation.objects.create(
                email=email,
                customer=customer,
                invited_by=request.user,
            )

            accept_url = absolute_view_url(
                "invitation_accept",
                request=request,
                kwargs={"token": invitation.token},
            )
            send_invitation_email(invitation, accept_url)
            log_activity(request.user, "invitation_sent", f"Invited {email} to {customer.name}", request)

            messages.success(request, f"Invitation sent to {email}")
            return redirect("admin_portal:customer_detail", pk=customer.id)
    else:
        form = SendInvitationForm()
        if customer_id:
            form.fields["customer"].initial = int(customer_id)

    return render(request, "admin_portal/send_invitation.html", {"form": form, "customer_id": customer_id})


def invitation_accept(request, token):
    try:
        invitation = get_object_or_404(CustomerInvitation, token=token)
        if not invitation.is_valid:
            context = {"error": "This invitation has expired or been used."}
            return render(request, "registration/accept_invitation.html", context)
    except CustomerInvitation.DoesNotExist:
        context = {"error": "Invalid invitation link."}
        return render(request, "registration/accept_invitation.html", context)

    if request.method == "POST":
        form = AcceptInvitationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=invitation.email,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    password=form.cleaned_data["password1"],
                    role=User.Role.CUSTOMER_USER,
                    customer=invitation.customer,
                    invited_by=invitation.invited_by,
                    is_active=True,
                )
                invitation.accepted_at = timezone.now()
                invitation.save()
                log_activity(user, "account_created", f"Account created from invitation", request)

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Your account has been created!")
            return redirect("customers:dashboard")
    else:
        form = AcceptInvitationForm()

    inviter = invitation.invited_by
    invited_by_name = (
        (inviter.get_full_name() or inviter.username)
        if inviter
        else "Pro Vibe Life"
    )

    return render(
        request,
        "registration/accept_invitation.html",
        {
            "form": form,
            "invitation": invitation,
            "invited_by_name": invited_by_name,
        },
    )


@sales_required
def admin_marketing_email_shilajit(request):
    if request.method == "POST":
        form = MarketingShilajitEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            store_name = (form.cleaned_data.get("store_name") or "").strip()
            first_name = (form.cleaned_data.get("first_name") or "").strip()
            last_name = (form.cleaned_data.get("last_name") or "").strip()

            with transaction.atomic():
                lead, _created = RetailerLead.objects.update_or_create(
                    email=email,
                    defaults={
                        "store_name": store_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "created_by": request.user,
                    },
                )
                token = RetailerAccountCreationToken.objects.create(
                    lead=lead,
                    created_by=request.user,
                )

            account_creation_url = absolute_view_url(
                "retailer_create_account",
                request=request,
                query={"token": str(token.token)},
            )
            send_retailer_shilajit_info_email(to=email, account_creation_url=account_creation_url)
            log_activity(
                request.user,
                "marketing_email_sent",
                f"Sent Shilajit retailer info email to {email}",
                request,
            )
            messages.success(request, f"Shilajit retailer info email sent to {email}")
            return redirect("admin_portal:marketing_email_shilajit")
    else:
        form = MarketingShilajitEmailForm()

    return render(
        request,
        "admin_portal/marketing_email_shilajit.html",
        {"form": form},
    )


@sales_required
def admin_marketing_emails(request):
    return render(request, "admin_portal/marketing_emails.html")


@sales_required
def admin_marketing_email_app_invite(request):
    if request.method == "POST":
        form = MarketingShilajitEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            store_name = (form.cleaned_data.get("store_name") or "").strip()
            first_name = (form.cleaned_data.get("first_name") or "").strip()
            last_name = (form.cleaned_data.get("last_name") or "").strip()

            with transaction.atomic():
                lead, _created = RetailerLead.objects.update_or_create(
                    email=email,
                    defaults={
                        "store_name": store_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "created_by": request.user,
                    },
                )
                token = RetailerAccountCreationToken.objects.create(
                    lead=lead,
                    created_by=request.user,
                )

            account_creation_url = absolute_view_url(
                "retailer_create_account",
                request=request,
                query={"token": str(token.token)},
            )
            send_retailer_app_invite_email(to=email, account_creation_url=account_creation_url)
            log_activity(
                request.user,
                "marketing_email_sent",
                f"Sent App Invite email to {email}",
                request,
            )
            messages.success(request, f"App invite email sent to {email}")
            return redirect("admin_portal:marketing_email_app_invite")
    else:
        form = MarketingShilajitEmailForm()

    return render(
        request,
        "admin_portal/marketing_email_app_invite.html",
        {"form": form},
    )


@sales_required
def admin_marketing_email_vitali_t(request):
    if request.method == "POST":
        form = MarketingShilajitEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            store_name = (form.cleaned_data.get("store_name") or "").strip()
            first_name = (form.cleaned_data.get("first_name") or "").strip()
            last_name = (form.cleaned_data.get("last_name") or "").strip()

            with transaction.atomic():
                lead, _created = RetailerLead.objects.update_or_create(
                    email=email,
                    defaults={
                        "store_name": store_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "created_by": request.user,
                    },
                )
                token = RetailerAccountCreationToken.objects.create(
                    lead=lead,
                    created_by=request.user,
                )

            account_creation_url = absolute_view_url(
                "retailer_create_account",
                request=request,
                query={"token": str(token.token)},
            )
            send_retailer_vitali_t_info_email(to=email, account_creation_url=account_creation_url)
            log_activity(
                request.user,
                "marketing_email_sent",
                f"Sent Vitali-T retailer info email to {email}",
                request,
            )
            messages.success(request, f"Vitali-T retailer info email sent to {email}")
            return redirect("admin_portal:marketing_email_vitali_t")
    else:
        form = MarketingShilajitEmailForm()

    return render(
        request,
        "admin_portal/marketing_email_vitali_t.html",
        {"form": form},
    )


@sales_required
def admin_marketing_email_preview(request, slug):
    sample_url = absolute_view_url(
        "retailer_create_account",
        request=request,
        query={"token": "preview-token"},
    )
    templates = {
        "shilajit": ("emails/retailer_shilajit_info.html", {"account_creation_url": sample_url}),
        "app-invite": ("emails/retailer_app_invite.html", {"account_creation_url": sample_url, "mobile_app_download_url": MOBILE_APP_DOWNLOAD_URL}),
        "vitali-t": ("emails/retailer_vitali_t_info.html", {"account_creation_url": sample_url}),
    }
    if slug not in templates:
        return HttpResponse("Not found", status=404)
    template_name, context = templates[slug]
    html = render_to_string(template_name, context)
    return HttpResponse(html)


def _derive_customer_name_from_email(email: str) -> str:
    local = (email.split("@", 1)[0] if email and "@" in email else email).strip()
    if not local:
        return "Retailer"
    return local.replace(".", " ").replace("_", " ").strip().title() or "Retailer"


def _unique_customer_name(base_name: str) -> str:
    base_name = (base_name or "").strip() or "Retailer"
    candidate = base_name
    i = 2
    while Customer.objects.filter(name=candidate).exists():
        candidate = f"{base_name} ({i})"
        i += 1
    return candidate


def retailer_create_account(request):
    token_raw = (request.GET.get("token") or "").strip()
    try:
        token_uuid = uuid.UUID(token_raw)
    except Exception:
        return render(
            request,
            "retailer/create_account.html",
            {"error": "Invalid or missing account creation link."},
        )

    token_obj = RetailerAccountCreationToken.objects.filter(token=token_uuid).select_related("lead").first()
    if not token_obj or not token_obj.is_valid:
        return render(
            request,
            "retailer/create_account.html",
            {"error": "This account creation link has expired or been used."},
        )

    lead = token_obj.lead
    existing_user = User.objects.filter(email__iexact=lead.email).first()
    if existing_user:
        # Don't allow creating a second user for the same email; push them to login/reset.
        return render(
            request,
            "retailer/create_account.html",
            {
                "error": (
                    "An account already exists for this email. Please sign in, or use password reset if needed."
                )
            },
        )

    if request.method == "POST":
        form = RetailerAccountCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Re-check validity inside the transaction for idempotency under retries.
                token_obj = (
                    RetailerAccountCreationToken.objects.select_for_update()
                    .select_related("lead")
                    .filter(token=token_uuid)
                    .first()
                )
                if not token_obj or not token_obj.is_valid:
                    return render(
                        request,
                        "retailer/create_account.html",
                        {"error": "This account creation link has expired or been used."},
                    )
                lead = token_obj.lead

                if User.objects.filter(email__iexact=lead.email).exists():
                    return render(
                        request,
                        "retailer/create_account.html",
                        {
                            "error": (
                                "An account already exists for this email. Please sign in, or use password reset if needed."
                            )
                        },
                    )

                store_name = (form.cleaned_data.get("store_name") or lead.store_name or "").strip()
                customer_name = _unique_customer_name(store_name or _derive_customer_name_from_email(lead.email))
                customer = Customer.objects.create(
                    name=customer_name,
                    is_active=True,
                )
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=lead.email,
                    first_name=form.cleaned_data.get("first_name") or lead.first_name,
                    last_name=form.cleaned_data.get("last_name") or lead.last_name,
                    password=form.cleaned_data["password1"],
                    role=User.Role.CUSTOMER_USER,
                    customer=customer,
                    is_active=True,
                )

                token_obj.used_at = timezone.now()
                token_obj.save()
                lead.created_customer = customer
                lead.store_name = store_name or lead.store_name
                lead.first_name = user.first_name or lead.first_name
                lead.last_name = user.last_name or lead.last_name
                lead.save(update_fields=["created_customer", "store_name", "first_name", "last_name", "updated_at"])

                log_activity(user, "retailer_account_created", "Retailer account created via marketing link", request)

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Your retailer account has been created!")
            return redirect("customers:dashboard")
    else:
        form = RetailerAccountCreateForm(
            initial={
                "store_name": lead.store_name,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
            }
        )

    return render(
        request,
        "retailer/create_account.html",
        {"form": form, "lead": lead},
    )


def custom_password_reset(request):
    if request.method == "POST":
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("password_reset_done")
    else:
        form = CustomPasswordResetForm()
    return render(request, "registration/password_reset_form.html", {"form": form})


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = "/accounts/reset/done/"

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.user, "password_reset_completed", request=self.request)
        return response


@sales_required
def admin_customer_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk, is_customer_user=True)
    if request.method == "POST":
        form = CustomerUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            try:
                updated_user = form.save()
                messages.success(request, "Customer user updated.")
                if updated_user.customer_id:
                    return redirect("admin_portal:customer_detail", pk=updated_user.customer_id)
                return redirect("admin_portal:customers")
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = CustomerUserUpdateForm(instance=user)

    return render(
        request,
        "admin_portal/customer_user_form.html",
        {"form": form, "form_title": "Edit Customer User", "submit_label": "Save User"},
    )


@admin_required
def admin_internal_users(request):
    internal_users = User.objects.filter(
        role__in=("sales_rep", "sales_lead", "warehouse_staff")
    ).order_by("role", "username")
    return render(request, "admin_portal/internal_users.html", {"users": internal_users})


@admin_required
def admin_internal_user_create(request):
    if request.method == "POST":
        form = InternalUserCreateForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f"{user.get_role_display()} user created.")
                return redirect("admin_portal:internal_users")
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = InternalUserCreateForm()

    return render(
        request,
        "admin_portal/internal_user_form.html",
        {"form": form, "form_title": "Create Internal User", "submit_label": "Create User"},
    )


@admin_required
def admin_internal_user_edit(request, pk):
    user = get_object_or_404(
        User, pk=pk, role__in=("sales_rep", "sales_lead", "warehouse_staff")
    )
    if request.method == "POST":
        form = InternalUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            try:
                updated_user = form.save()
                messages.success(request, f"{updated_user.get_role_display()} user updated.")
                return redirect("admin_portal:internal_users")
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = InternalUserUpdateForm(instance=user)

    return render(
        request,
        "admin_portal/internal_user_form.html",
        {"form": form, "form_title": f"Edit {user.get_role_display()}", "submit_label": "Save User"},
    )


@admin_required
def admin_user_activity(request, pk):
    user = get_object_or_404(User, pk=pk)
    activities = user.activity_logs.all()[:100]
    return render(
        request,
        "admin_portal/user_activity.html",
        {"user": user, "activities": activities},
    )


@customer_required
def customer_activity(request):
    activities = request.user.activity_logs.all()[:100]
    return render(request, "customer/activity.html", {"activities": activities})
