from django.contrib.auth.signals import user_logged_in, user_logged_out
from accounts.activity import log_activity


def on_login(sender, request, user, **kwargs):
    log_activity(user, "login", request=request)


def on_logout(sender, request, user, **kwargs):
    log_activity(user, "logout", request=request)


user_logged_in.connect(on_login)
user_logged_out.connect(on_logout)
