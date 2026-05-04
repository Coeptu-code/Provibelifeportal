from django import forms

from pricing.models import CustomerPrice, CustomerProduct


class CustomerProductForm(forms.ModelForm):
    class Meta:
        model = CustomerProduct
        fields = ["customer", "product", "active"]


class CustomerPriceForm(forms.ModelForm):
    class Meta:
        model = CustomerPrice
        fields = [
            "customer",
            "product",
            "unit_price",
            "minimum_quantity",
            "effective_date",
            "expiration_date",
        ]
