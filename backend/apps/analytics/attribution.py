from django.db.models import Exists, OuterRef, Q, Subquery

from .models import WebSession


def with_first_touch(queryset):
    """Annotate leads using their earliest attributable web session."""
    linked_visitors = WebSession.objects.filter(
        lead_id=OuterRef(OuterRef("pk")),
    ).values("visitor_id")
    conflicting_lead = WebSession.objects.filter(
        visitor_id=OuterRef("visitor_id"), lead__isnull=False,
    ).exclude(lead_id=OuterRef(OuterRef("pk")))
    first = WebSession.objects.filter(
        visitor_id__in=Subquery(linked_visitors),
    ).annotate(
        visitor_has_conflicting_lead=Exists(conflicting_lead),
    ).filter(
        Q(lead_id=OuterRef("pk"))
        | Q(lead__isnull=True, visitor_has_conflicting_lead=False),
    ).order_by("started_at", "id")
    return queryset.annotate(
        first_session_id=Subquery(first.values("id")[:1]),
        acquired_at=Subquery(first.values("started_at")[:1]),
        acquired_campaign=Subquery(first.values("utm_campaign")[:1]),
        acquired_source=Subquery(first.values("utm_source")[:1]),
        acquired_medium=Subquery(first.values("utm_medium")[:1]),
        acquired_content=Subquery(first.values("utm_content")[:1]),
    )


def first_touch_session(lead):
    linked_visitor_ids = set(
        WebSession.objects.filter(lead=lead).values_list("visitor_id", flat=True),
    )
    conflicting_visitor_ids = set(
        WebSession.objects.filter(
            visitor_id__in=linked_visitor_ids, lead__isnull=False,
        ).exclude(lead=lead).values_list("visitor_id", flat=True),
    )
    safe_visitor_ids = linked_visitor_ids - conflicting_visitor_ids
    return WebSession.objects.filter(
        Q(lead=lead) | Q(lead__isnull=True, visitor_id__in=safe_visitor_ids),
    ).order_by("started_at", "id").first()
