import csv
import io
import json
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
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
from accounts.url_utils import absolute_path, absolute_view_url
from accounts.forms import (
    AcceptInvitationForm, CustomPasswordResetForm, CustomerUserCreateForm, CustomerUserUpdateForm,
    InternalUserCreateForm, InternalUserUpdateForm, SendInvitationForm, MarketingShilajitEmailForm,
    MarketingFreeSampleLinkForm,
    RetailerAccountCreateForm,
)
from accounts.models import (
    CustomerInvitation,
    RetailerLead,
    RetailerAccountCreationToken,
    RetailerMarketingPageToken,
)
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
            phone = (form.cleaned_data.get("phone") or "").strip()

            with transaction.atomic():
                lead, _created = RetailerLead.objects.update_or_create(
                    email=email,
                    defaults={
                        "store_name": store_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": phone,
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
            phone = (form.cleaned_data.get("phone") or "").strip()

            with transaction.atomic():
                lead, _created = RetailerLead.objects.update_or_create(
                    email=email,
                    defaults={
                        "store_name": store_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": phone,
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
            phone = (form.cleaned_data.get("phone") or "").strip()

            with transaction.atomic():
                lead, _created = RetailerLead.objects.update_or_create(
                    email=email,
                    defaults={
                        "store_name": store_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": phone,
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


def _upsert_retailer_lead_from_form(*, form, user):
    email = form.cleaned_data["email"].strip().lower()
    store_name = (form.cleaned_data.get("store_name") or "").strip()
    first_name = (form.cleaned_data.get("first_name") or "").strip()
    last_name = (form.cleaned_data.get("last_name") or "").strip()
    phone = (form.cleaned_data.get("phone") or "").strip()
    lead, _created = RetailerLead.objects.update_or_create(
        email=email,
        defaults={
            "store_name": store_name,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "created_by": user,
        },
    )
    return lead


def _new_free_sample_token(*, lead, request, created_by=None, source=""):
    token = RetailerMarketingPageToken.objects.create(
        lead=lead,
        page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE,
        source=(source or "").strip(),
        created_by=created_by,
    )
    token_url = absolute_path("/pages/free-sample/", request=request, query={"token": str(token.token)})
    return token, token_url


def _free_sample_token_url(*, token_obj, request):
    return absolute_path("/pages/free-sample/", request=request, query={"token": str(token_obj.token)})


def _client_ip(request) -> str | None:
    x_forwarded_for = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip() or None
    return (request.META.get("REMOTE_ADDR") or "").strip() or None


def _parse_bulk_leads_text(raw_text: str) -> list[dict]:
    text = (raw_text or "").strip()
    if not text:
        return []

    if text.startswith("[") or text.startswith("{"):
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("leads"), list):
            parsed = parsed["leads"]
        if not isinstance(parsed, list):
            raise ValueError("JSON must be a list or object with a leads list.")
        return [row for row in parsed if isinstance(row, dict)]

    rows: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        normalized = {str(k or "").strip(): (v or "").strip() for k, v in row.items()}
        rows.append(normalized)
    return rows


def _bulk_row_email(row: dict) -> str:
    return (
        (row.get("email") or row.get("send_email") or row.get("primary_contact_email") or "")
        .strip()
        .lower()
    )


def _bulk_row_bool(row: dict, key: str, default=False) -> bool:
    raw = str(row.get(key) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y"}


def _token_csv_response(request, tokens: list[RetailerMarketingPageToken]) -> HttpResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    # Lightweight export format for Ecompiner imports.
    writer.writerow(["email", "token"])
    for token_obj in tokens:
        lead = token_obj.lead
        writer.writerow([lead.email, str(token_obj.token)])
    csv_body = output.getvalue()
    response = HttpResponse(csv_body, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="free_sample_tokens.csv"'
    return response


def free_sample_page(request, token=None):
    token_raw = str(token or request.GET.get("token") or request.GET.get("t") or "").strip()
    try:
        token_uuid = uuid.UUID(token_raw)
    except Exception:
        raise Http404("Invalid or missing token")

    token_obj = (
        RetailerMarketingPageToken.objects.select_related("lead")
        .filter(
            token=token_uuid,
            page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE,
        )
        .first()
    )
    if not token_obj or not token_obj.is_valid:
        raise Http404("Token is invalid or expired")

    token_obj.mark_clicked(
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    lead = token_obj.lead

    submission_success = False
    if request.method == "POST":
        submission_success = True
        actor = token_obj.created_by or lead.created_by
        if actor:
            log_activity(
                actor,
                "free_sample_form_submitted",
                f"Free sample form submitted for lead {lead.email}",
                request,
            )

    return render(
        request,
        "public/free_sample.html",
        {
            "lead": lead,
            "token": token_obj,
            "submission_success": submission_success,
        },
    )


@sales_required
def admin_marketing_free_sample_links(request):
    generated_link = ""
    generated_token = None
    reused_existing_token = False
    reuse_active = True

    if request.method == "POST":
        form = MarketingFreeSampleLinkForm(request.POST)
        reuse_active = request.POST.get("reuse_active", "1") == "1"
        if form.is_valid():
            with transaction.atomic():
                lead = _upsert_retailer_lead_from_form(form=form, user=request.user)
                source = (form.cleaned_data.get("source") or "").strip()
                if reuse_active:
                    existing_active = (
                        RetailerMarketingPageToken.objects.filter(
                            lead=lead,
                            page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE,
                            source=source,
                            expires_at__gt=timezone.now(),
                        )
                        .order_by("-created_at")
                        .first()
                    )
                    if existing_active:
                        generated_token = existing_active
                        generated_link = _free_sample_token_url(token_obj=existing_active, request=request)
                        reused_existing_token = True
                    else:
                        generated_token, generated_link = _new_free_sample_token(
                            lead=lead,
                            request=request,
                            created_by=request.user,
                            source=source,
                        )
                else:
                    generated_token, generated_link = _new_free_sample_token(
                        lead=lead,
                        request=request,
                        created_by=request.user,
                        source=source,
                    )
            log_activity(
                request.user,
                "free_sample_token_generated",
                f"Generated free-sample token for {lead.email}",
                request,
            )
            if reused_existing_token:
                messages.success(request, "Reused active tokenized free-sample link.")
            else:
                messages.success(request, "Tokenized free-sample link generated.")
    else:
        form = MarketingFreeSampleLinkForm()

    recent_tokens = (
        RetailerMarketingPageToken.objects.select_related("lead", "created_by")
        .filter(page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE)
        .order_by("-created_at")[:25]
    )

    return render(
        request,
        "admin_portal/marketing_free_sample_links.html",
        {
            "form": form,
            "generated_link": generated_link,
            "generated_token": generated_token,
            "reused_existing_token": reused_existing_token,
            "reuse_active": reuse_active,
            "recent_tokens": recent_tokens,
            "now": timezone.now(),
        },
    )


@sales_required
def admin_marketing_free_sample_token_generator(request):
    bulk_text = ""
    source = ""
    is_test = False
    generated_rows = []
    failures = []

    if request.method == "POST":
        action = (request.POST.get("action") or "generate").strip().lower()
        if action == "download":
            token_ids = request.session.get("free_sample_bulk_token_ids", [])
            tokens = list(
                RetailerMarketingPageToken.objects.select_related("lead")
                .filter(id__in=token_ids, page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE)
                .order_by("id")
            )
            if not tokens:
                messages.error(request, "No generated tokens available for download yet.")
            else:
                return _token_csv_response(request, tokens)

        bulk_text = request.POST.get("bulk_text", "")
        source = (request.POST.get("source") or "").strip()
        is_test = request.POST.get("is_test") == "1"

        try:
            rows = _parse_bulk_leads_text(bulk_text)
            if not rows:
                raise ValueError("No lead rows found. Paste CSV/JSON rows first.")

            token_ids = []
            with transaction.atomic():
                for idx, row in enumerate(rows):
                    try:
                        email = _bulk_row_email(row)
                        if not email:
                            raise ValueError("Missing email/send_email/primary_contact_email.")
                        lead, _ = RetailerLead.objects.update_or_create(
                            email=email,
                            defaults={
                                "store_name": (
                                    row.get("store_name")
                                    or row.get("name")
                                    or row.get("business_name")
                                    or ""
                                ).strip(),
                                "first_name": (row.get("first_name") or "").strip(),
                                "last_name": (row.get("last_name") or "").strip(),
                                "phone": (row.get("phone") or "").strip(),
                                "created_by": request.user,
                            },
                        )
                        token_obj = RetailerMarketingPageToken.objects.create(
                            lead=lead,
                            page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE,
                            source=source or (row.get("source") or row.get("token_source") or "").strip(),
                            created_by=request.user,
                            is_test=is_test or _bulk_row_bool(row, "is_test"),
                        )
                        token_ids.append(token_obj.id)
                        generated_rows.append(
                            {
                                "email": lead.email,
                                "token": str(token_obj.token),
                                "source": token_obj.source,
                                "is_test": token_obj.is_test,
                                "url": _free_sample_token_url(token_obj=token_obj, request=request),
                            }
                        )
                    except Exception as exc:
                        failures.append({"index": idx, "error": str(exc), "row": row})

            request.session["free_sample_bulk_token_ids"] = token_ids
            messages.success(
                request,
                f"Generated {len(generated_rows)} token(s). Failed rows: {len(failures)}.",
            )
            log_activity(
                request.user,
                "free_sample_tokens_bulk_generated",
                f"Bulk generated {len(generated_rows)} free-sample tokens",
                request,
            )
        except Exception as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "admin_portal/marketing_free_sample_token_generator.html",
        {
            "bulk_text": bulk_text,
            "source": source,
            "is_test": is_test,
            "generated_rows": generated_rows,
            "failures": failures,
        },
    )


@sales_required
def admin_marketing_free_sample_clicks(request):
    q = (request.GET.get("q") or "").strip()
    clicked = (request.GET.get("clicked") or "all").strip().lower()
    status = (request.GET.get("status") or "all").strip().lower()
    source = (request.GET.get("source") or "").strip()
    test = (request.GET.get("is_test") or "all").strip().lower()
    page_number = request.GET.get("page") or 1

    base_tokens = (
        RetailerMarketingPageToken.objects.select_related("lead", "created_by")
        .filter(page_slug=RetailerMarketingPageToken.PageSlug.FREE_SAMPLE)
    )
    tokens = base_tokens
    if q:
        tokens = tokens.filter(
            Q(lead__email__icontains=q)
            | Q(lead__phone__icontains=q)
            | Q(lead__store_name__icontains=q)
            | Q(source__icontains=q)
            | Q(token__icontains=q)
        )
    if source:
        tokens = tokens.filter(source__iexact=source)
    if test == "yes":
        tokens = tokens.filter(is_test=True)
    elif test == "no":
        tokens = tokens.filter(is_test=False)
    if clicked == "yes":
        tokens = tokens.filter(click_count__gt=0)
    elif clicked == "no":
        tokens = tokens.filter(click_count=0)

    now = timezone.now()
    if status == "active":
        tokens = tokens.filter(expires_at__gt=now)
    elif status == "expired":
        tokens = tokens.filter(expires_at__lte=now)

    tokens = tokens.order_by("-last_clicked_at", "-created_at")
    paginator = Paginator(tokens, 100)
    page_obj = paginator.get_page(page_number)

    source_options = (
        base_tokens.exclude(source="")
        .order_by("source")
        .values_list("source", flat=True)
        .distinct()
    )
    total = base_tokens.count()
    clicked_count = base_tokens.filter(click_count__gt=0).count()
    total_clicks = base_tokens.aggregate(sum_clicks=Sum("click_count")).get("sum_clicks") or 0

    return render(
        request,
        "admin_portal/marketing_free_sample_clicks.html",
        {
            "tokens": page_obj.object_list,
            "page_obj": page_obj,
            "q": q,
            "clicked_filter": clicked,
            "status_filter": status,
            "test_filter": test,
            "source_filter": source,
            "source_options": source_options,
            "total": total,
            "clicked": clicked_count,
            "total_clicks": total_clicks,
            "filtered_count": tokens.count(),
            "now": now,
        },
    )


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
