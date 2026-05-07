from django import forms

from customers.models import Customer, ShippingAddress


class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = [
            "label",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "is_active",
        ]


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name",
            "payment_terms",
            "preferred_carrier",
            "credit_limit",
            "is_active",
            "shopify_customer_id",
            "stripe_customer_id",
            "sales_rep",
        ]


class AdminShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = [
            "customer",
            "label",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "is_active",
        ]
