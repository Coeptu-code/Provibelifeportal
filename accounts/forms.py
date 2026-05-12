from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from customers.models import Customer


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

    def _post_clean(self):
        # role must be set before model.clean() runs so the role/customer
        # constraint doesn't fire against the model's "admin" default
        self.instance.role = User.Role.CUSTOMER_USER
        super()._post_clean()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER_USER
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

    def _post_clean(self):
        self.instance.role = User.Role.CUSTOMER_USER
        super()._post_clean()

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


class InternalUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "manager",
            "is_active",
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class InternalUserUpdateForm(forms.ModelForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput, min_length=8, required=False)
    new_password2 = forms.CharField(widget=forms.PasswordInput, min_length=8, required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "manager",
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
        if self.cleaned_data.get("new_password1"):
            user.set_password(self.cleaned_data["new_password1"])
        if commit:
            user.save()
        return user


class SendInvitationForm(forms.Form):
    email = forms.EmailField()
    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(is_active=True))


class AcceptInvitationForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("username") and User.objects.filter(username=cleaned["username"]).exists():
            raise forms.ValidationError("This username is already taken.")
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class CustomPasswordResetForm(PasswordResetForm):
    def save(self, **kwargs):
        from accounts.email_service import send_password_reset_email
        from accounts.url_utils import absolute_view_url
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        email = self.cleaned_data["email"]
        users = User.objects.filter(email__iexact=email, is_active=True)

        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = absolute_view_url(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": token},
            )
            send_password_reset_email(user, reset_url)

        # We intentionally bypass Django's default email sender because this
        # project uses Resend via send_password_reset_email above.
        return None


class MarketingShilajitEmailForm(forms.Form):
    email = forms.EmailField(label="Recipient Email")
    store_name = forms.CharField(label="Store Name", max_length=255, required=False)
    first_name = forms.CharField(label="First Name", max_length=150, required=False)
    last_name = forms.CharField(label="Last Name", max_length=150, required=False)
    phone = forms.CharField(label="Phone Number", max_length=50, required=False)


class MarketingFreeSampleLinkForm(MarketingShilajitEmailForm):
    source = forms.CharField(
        label="Campaign Source",
        max_length=120,
        required=False,
        help_text="Optional label like `may-2026-shilajit-blast` for reporting.",
    )


class RetailerAccountCreateForm(forms.Form):
    store_name = forms.CharField(label="Store Name", max_length=255, required=False)
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned
