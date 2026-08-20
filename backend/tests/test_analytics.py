import pytest
from django.utils import timezone
from apps.analytics.models import AnonymousVisitor, WebSession


@pytest.mark.django_db
def test_analytics_rejects_unknown_and_invalid_payload(client):
    visitor = AnonymousVisitor.objects.create(first_seen_at=timezone.now(), last_seen_at=timezone.now())
    session = WebSession.objects.create(visitor=visitor, started_at=timezone.now(), last_seen_at=timezone.now(), landing_path="/", consent_state="ESSENTIAL")
    base = {"occurred_at": timezone.now().isoformat(), "visitor_id": str(visitor.id), "session_id": str(session.id), "schema_version": 1, "properties": {}}
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "invented_event"}, content_type="application/json").status_code == 400
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "filter_applied"}, content_type="application/json").status_code == 400
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "page_viewed", "page_path": "/"}, content_type="application/json").status_code == 201
