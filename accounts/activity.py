from accounts.models import ActivityLog


def log_activity(user, action: str, detail: str = "", request=None) -> None:
    ip = None
    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
    ActivityLog.objects.create(user=user, action=action, detail=detail, ip_address=ip or None)
