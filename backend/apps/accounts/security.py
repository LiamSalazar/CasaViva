from datetime import datetime, timedelta

from django.utils import timezone


def has_recent_mfa(request, *, minutes=15):
    value = request.session.get("mfa_verified_at")
    if not value:
        return False
    try:
        verified_at = datetime.fromisoformat(value)
        if timezone.is_naive(verified_at):
            verified_at = timezone.make_aware(verified_at)
    except (TypeError, ValueError):
        return False
    return timezone.now() - verified_at <= timedelta(minutes=minutes)
