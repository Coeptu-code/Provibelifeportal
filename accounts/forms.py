from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


class CustomerUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "customer",
            "is_active",
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER_USER
        user.is_customer_user = True
        user.is_ops_user = False
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomerUserUpdateForm(forms.ModelForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput, min_length=8, required=False)
    new_password2 = forms.CharField(widget=forms.PasswordInput, min_length=8, required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "customer",
            "is_active",
        ]

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if (p1 or p2) and p1 != p2:
            raise forms.ValidationError("New passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER_USER
        user.is_customer_user = True
        user.is_ops_user = False
        if self.cleaned_data.get("new_password1"):
            user.set_password(self.cleaned_data["new_password1"])
        if commit:
            user.save()
        return user
