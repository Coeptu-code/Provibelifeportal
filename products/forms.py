from django import forms

from products.models import Product


class ProductForm(forms.ModelForm):
    image_upload = forms.ImageField(required=False, label="Product image")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sku"].required = False
        if self.instance and self.instance.pk:
            self.fields["sku"].disabled = True
            self.fields["sku"].widget = forms.TextInput(attrs={"readonly": "readonly"})
        else:
            self.fields["sku"].widget = forms.HiddenInput()

    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "description",
            "image_upload",
            "case_quantity",
            "shipping_weight",
            "shipping_weight_unit",
            "shipping_length",
            "shipping_width",
            "shipping_height",
            "shipping_dimension_unit",
            "shipping_package_type",
            "active",
        ]
