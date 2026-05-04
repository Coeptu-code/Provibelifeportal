from datetime import date

from django.core.exceptions import ValidationError

from pricing.models import CustomerPrice


def get_active_customer_price(customer, product, as_of=None):
    as_of = as_of or date.today()
    prices = CustomerPrice.objects.filter(
        customer=customer,
        product=product,
        effective_date__lte=as_of,
    ).order_by("-effective_date")

    active = [p for p in prices if p.expiration_date is None or p.expiration_date >= as_of]
    if not active:
        raise ValidationError(
            f"No active negotiated price for customer={customer.id} product={product.id}."
        )
    return active[0]
