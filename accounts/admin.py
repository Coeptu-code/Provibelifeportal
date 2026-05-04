from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class PortalUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + (
        ("Portal Role", {"fields": ("role", "customer")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Portal Role", {"fields": ("role", "customer")}),
    )
