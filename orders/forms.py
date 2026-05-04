from django import forms

from customers.models import ShippingAddress


class CustomerOrderForm(forms.Form):
    po_number = forms.CharField(max_length=100, required=False)
    requested_ship_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    shipping_address = forms.ModelChoiceField(queryset=ShippingAddress.objects.none())

    def __init__(self, *args, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shipping_address"].queryset = ShippingAddress.objects.filter(
            customer=customer, is_active=True
        ).order_by("-is_default", "label")
