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
