from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def customer_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_customer_user:
            raise PermissionDenied("Customer access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def ops_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not (request.user.is_ops_user or request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Operations access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != "admin":
            raise PermissionDenied("Admin access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def sales_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role not in ("admin", "sales_lead", "sales_rep"):
            raise PermissionDenied("Sales access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def warehouse_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role not in ("admin", "warehouse_staff"):
            raise PermissionDenied("Warehouse access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped
