from django.db import transaction
from django.utils import timezone

from invoicing.models import Invoice, InvoiceStatus
from payments.models import StripeWebhookEvent


def _map_invoice_status(stripe_invoice):
    status = stripe_invoice.get("status")
    amount_paid = stripe_invoice.get("amount_paid", 0)
    amount_remaining = stripe_invoice.get("amount_remaining", 0)

    if status == "paid":
        return InvoiceStatus.PAID
    if status == "void":
        return InvoiceStatus.VOID
    if status == "open":
        if amount_paid > 0 and amount_remaining > 0:
            return InvoiceStatus.PARTIALLY_PAID
        if stripe_invoice.get("due_date") and stripe_invoice.get("status_transitions", {}).get("paid_at") is None:
            return InvoiceStatus.OPEN
    if status == "draft":
        return InvoiceStatus.DRAFT
    return InvoiceStatus.OPEN


@transaction.atomic
def process_stripe_event(event):
    event_id = event["id"]
    event_type = event["type"]
    receipt, created = StripeWebhookEvent.objects.get_or_create(
        event_id=event_id, defaults={"event_type": event_type}
    )
    if not created and receipt.processed_at:
        return False

    data_object = event["data"]["object"]
    stripe_invoice_id = data_object.get("id")
    if stripe_invoice_id:
        invoice = Invoice.objects.filter(stripe_invoice_id=stripe_invoice_id).first()
        if invoice:
            mapped_status = _map_invoice_status(data_object)
            invoice.status = mapped_status
            if event_type == "invoice.paid":
                invoice.paid_at = timezone.now()
            invoice.save(update_fields=["status", "paid_at"])

    receipt.processed_at = timezone.now()
    receipt.save(update_fields=["processed_at"])
    return True
