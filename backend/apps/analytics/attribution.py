from django.db.models import OuterRef, Subquery

from .models import WebSession


def with_first_touch(queryset):
    """Annotate leads using their earliest attributable web session."""
    first = WebSession.objects.filter(lead_id=OuterRef("pk")).order_by("started_at", "id")
    return queryset.annotate(
        first_session_id=Subquery(first.values("id")[:1]),
        acquired_at=Subquery(first.values("started_at")[:1]),
        acquired_campaign=Subquery(first.values("utm_campaign")[:1]),
        acquired_source=Subquery(first.values("utm_source")[:1]),
        acquired_medium=Subquery(first.values("utm_medium")[:1]),
        acquired_content=Subquery(first.values("utm_content")[:1]),
    )


def first_touch_session(lead):
    return WebSession.objects.filter(lead=lead).order_by("started_at", "id").first()
