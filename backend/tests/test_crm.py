from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.analytics.models import AnalyticsEvent, AnonymousVisitor, WebSession
from apps.audit.models import AuditEvent
from apps.crm.models import ConsentRecord, Inquiry, Lead, LeadStageHistory, PrivacyNoticeVersion, Sale, Visit


@pytest.mark.django_db
def test_lead_stage_changes_close_previous_history_and_open_new(admin_client):
    create = admin_client.post(
        "/api/v1/admin/leads/",
        {"first_name": "Cliente", "email": "cliente@example.test", "status": "NEW"},
        format="json",
    )
    assert create.status_code == 201, create.data
    lead = Lead.objects.get(pk=create.data["id"])
    initial = LeadStageHistory.objects.get(lead=lead, ended_at__isnull=True)
    update = admin_client.patch(
        f"/api/v1/admin/leads/{lead.id}/",
        {"status": "CONTACTED", "version": lead.version},
        format="json",
    )
    assert update.status_code == 200, update.data
    initial.refresh_from_db()
    assert initial.ended_at is not None
    assert LeadStageHistory.objects.get(lead=lead, ended_at__isnull=True).stage == "CONTACTED"
    invalid = admin_client.patch(f"/api/v1/admin/leads/{lead.id}/", {"status": "WHATEVER", "version": update.data["version"]}, format="json")
    assert invalid.status_code == 400


@pytest.mark.django_db
def test_inquiry_deduplication_phone_and_ambiguous_identity(client, catalog):
    call_command("seed_system")
    base = {"first_name": "Uno", "phone": "55 1234 5678", "message": "Información", "listing_slug": catalog["listing"].slug, "privacy_consent": True}
    assert client.post("/api/v1/public/inquiries/", base, format="json").status_code == 201
    assert client.post("/api/v1/public/inquiries/", {**base, "phone": "+52 55 1234 5678"}, format="json").status_code == 201
    assert Lead.objects.count() == 1
    assert Inquiry.objects.count() == 2

    lead = Lead.objects.get()
    lead.email = "first@example.test"
    lead.save()
    ambiguous = {**base, "first_name": "Dos", "email": "second@example.test"}
    assert client.post("/api/v1/public/inquiries/", ambiguous, format="json").status_code == 201
    assert Lead.objects.count() == 2


@pytest.mark.django_db
def test_privacy_consent_requires_and_records_active_notice(client, catalog):
    call_command("seed_system")
    notice = PrivacyNoticeVersion.objects.get(is_active=True)
    payload = {"first_name": "Consentimiento", "email": "consent@example.test", "privacy_consent": True, "privacy_notice_version": str(notice.id)}
    accepted = client.post("/api/v1/public/inquiries/", payload, format="json")
    assert accepted.status_code == 201, accepted.data
    consent = ConsentRecord.objects.get(lead__email="consent@example.test")
    assert consent.privacy_notice_version == notice
    assert consent.granted is True
    rejected = client.post("/api/v1/public/inquiries/", {**payload, "email": "no@example.test", "privacy_consent": False}, format="json")
    assert rejected.status_code == 400


@pytest.mark.django_db
def test_inquiry_intent_subject_and_consent_purpose_are_preserved(client, catalog):
    call_command("seed_system")
    general = client.post("/api/v1/public/inquiries/", {"first_name": "General", "email": "general-intent@example.test", "privacy_consent": True, "intent": "GENERAL_CONTACT", "subject": "SEARCH_ASSISTANCE"}, format="json")
    visit = client.post("/api/v1/public/inquiries/", {"first_name": "Visita", "email": "visit-intent@example.test", "privacy_consent": True, "intent": "VISIT_REQUEST", "listing_slug": catalog["listing"].slug}, format="json")
    assert general.status_code == visit.status_code == 201
    assert Inquiry.objects.get(pk=general.data["id"]).subject == "SEARCH_ASSISTANCE"
    assert Inquiry.objects.get(pk=visit.data["id"]).intent == "VISIT_REQUEST"
    assert ConsentRecord.objects.get(lead__email="general-intent@example.test").purpose == "GENERAL_CONTACT"
    assert ConsentRecord.objects.get(lead__email="visit-intent@example.test").purpose == "VISIT_REQUEST"
    assert Visit.objects.count() == 0


@pytest.mark.django_db
def test_visit_crud_and_sale_preserves_financial_snapshot(admin_client, owner, catalog):
    lead = Lead.objects.create(first_name="Comprador", status="NEGOTIATING")
    LeadStageHistory.objects.create(lead=lead, stage="NEGOTIATING", started_at=timezone.now())
    visit = admin_client.post(
        "/api/v1/admin/visits/",
        {"lead": str(lead.id), "offering": str(catalog["offering"].id), "scheduled_at": timezone.now().isoformat(), "status": "SCHEDULED"},
        format="json",
    )
    assert visit.status_code == 201, visit.data
    completed = admin_client.patch(
        f"/api/v1/admin/visits/{visit.data['id']}/",
        {"status": "COMPLETED", "completed_at": timezone.now().isoformat()},
        format="json",
    )
    assert completed.status_code == 200

    catalog["offering"].default_commission_rate = Decimal("5.00")
    catalog["offering"].save()
    sale_response = admin_client.post(
        "/api/v1/admin/sales/",
        {
            "lead": str(lead.id), "offering": str(catalog["offering"].id), "listing": str(catalog["listing"].id),
            "sale_price": "1000000.00", "closed_at": timezone.now().isoformat(), "status": "CLOSED",
        },
        format="json",
    )
    assert sale_response.status_code == 201, sale_response.data
    sale = Sale.objects.get(pk=sale_response.data["id"])
    assert sale.commission_rate == Decimal("5.00")
    assert sale.commission_amount == Decimal("50000.00")
    catalog["offering"].default_commission_rate = Decimal("8.00")
    catalog["offering"].save()
    sale.refresh_from_db()
    assert sale.commission_rate == Decimal("5.00")
    assert sale.commission_amount == Decimal("50000.00")
    assert Lead.objects.get(pk=lead.pk).status == "WON"
    immutable = admin_client.patch(f"/api/v1/admin/sales/{sale.id}/", {"sale_price": "2.00"}, format="json")
    assert immutable.status_code == 400


@pytest.mark.django_db
def test_public_inquiry_listing_and_session_attribution(client, catalog):
    call_command("seed_system")
    now = timezone.now()
    visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    session = WebSession.objects.create(
        visitor=visitor, started_at=now, last_seen_at=now, landing_path="/?utm_campaign=atribucion",
        consent_state="ESSENTIAL", utm_source="instagram", utm_medium="paid_social",
        utm_campaign="tecamac_agosto", utm_content="reel_04",
    )
    event = AnalyticsEvent.objects.create(
        occurred_at=now, event_name="listing_viewed", schema_version=1, visitor=visitor,
        session=session, listing=catalog["listing"], offering=catalog["offering"], properties={},
    )
    payload = {
        "first_name": "Atribuido", "email": "atribuido@example.test", "privacy_consent": True,
        "listing_slug": catalog["listing"].slug, "session_id": str(session.id), "visitor_id": str(visitor.id),
    }
    response = client.post("/api/v1/public/inquiries/", payload, format="json")
    assert response.status_code == 201, response.data
    inquiry = Inquiry.objects.get(pk=response.data["id"])
    session.refresh_from_db(); event.refresh_from_db()
    assert inquiry.listing == catalog["listing"]
    assert inquiry.session_id == session.id
    assert session.lead == inquiry.lead
    assert event.lead == inquiry.lead
    assert inquiry.lead.first_source == "instagram"
    attribution = client.get(f"/api/v1/admin/bi/sessions/{session.id}/")
    assert attribution.status_code in (401, 403)


@pytest.mark.django_db
def test_public_inquiry_validates_listing_and_session_conflicts(client, catalog):
    call_command("seed_system")
    general = client.post(
        "/api/v1/public/inquiries/",
        {"first_name": "General", "email": "general@example.test", "privacy_consent": True},
        format="json",
    )
    assert general.status_code == 201
    missing_listing = client.post(
        "/api/v1/public/inquiries/",
        {"first_name": "Error", "email": "missing@example.test", "privacy_consent": True, "listing_slug": "no-existe"},
        format="json",
    )
    assert missing_listing.status_code == 400
    unknown_visitor = AnonymousVisitor.objects.create(first_seen_at=timezone.now(), last_seen_at=timezone.now())
    missing_session = client.post(
        "/api/v1/public/inquiries/",
        {"first_name": "Error", "email": "session@example.test", "privacy_consent": True, "session_id": "00000000-0000-0000-0000-000000000099", "visitor_id": str(unknown_visitor.id)},
        format="json",
    )
    assert missing_session.status_code == 400

    now = timezone.now()
    existing_lead = Lead.objects.create(first_name="Existente", email="existente@example.test")
    visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    session = WebSession.objects.create(visitor=visitor, lead=existing_lead, started_at=now, last_seen_at=now, landing_path="/", consent_state="ESSENTIAL")
    wrong_visitor = client.post(
        "/api/v1/public/inquiries/",
        {"first_name": "Otra", "email": "otra@example.test", "privacy_consent": True, "session_id": str(session.id), "visitor_id": str(unknown_visitor.id)},
        format="json",
    )
    assert wrong_visitor.status_code == 400
    incompatible = client.post(
        "/api/v1/public/inquiries/",
        {"first_name": "Otra", "email": "otra@example.test", "privacy_consent": True, "session_id": str(session.id), "visitor_id": str(visitor.id)},
        format="json",
    )
    assert incompatible.status_code == 400
    assert Lead.objects.filter(email="otra@example.test").count() == 0


@pytest.mark.django_db
def test_sale_status_transitions_are_persisted_coherent_audited_and_not_deletable(admin_client, catalog):
    lead = Lead.objects.create(first_name="Venta", status="NEGOTIATING")
    LeadStageHistory.objects.create(lead=lead, stage="NEGOTIATING", started_at=timezone.now())
    payload = {
        "lead": str(lead.id), "offering": str(catalog["offering"].id), "listing": str(catalog["listing"].id),
        "sale_price": "1000000.00", "closed_at": timezone.now().isoformat(), "status": "CANCELLED",
    }
    created = admin_client.post("/api/v1/admin/sales/", payload, format="json")
    assert created.status_code == 201, created.data
    sale = Sale.objects.get(pk=created.data["id"])
    assert sale.status == "CANCELLED"
    lead.refresh_from_db(); assert lead.status == "NEGOTIATING"

    closed = admin_client.patch(f"/api/v1/admin/sales/{sale.id}/", {"status": "CLOSED"}, format="json")
    assert closed.status_code == 200, closed.data
    sale.refresh_from_db(); lead.refresh_from_db()
    assert sale.status == "CLOSED" and lead.status == "WON"
    assert AuditEvent.objects.filter(entity_id=str(sale.id), action="SALE_STATUS_CHANGED").exists()

    cancelled = admin_client.patch(f"/api/v1/admin/sales/{sale.id}/", {"status": "CANCELLED"}, format="json")
    assert cancelled.status_code == 200, cancelled.data
    sale.refresh_from_db(); lead.refresh_from_db()
    assert sale.status == "CANCELLED" and lead.status == "NEGOTIATING"
    assert admin_client.delete(f"/api/v1/admin/sales/{sale.id}/").status_code == 405
    assert admin_client.delete(f"/api/v1/admin/visits/{Visit.objects.create(lead=lead, offering=catalog['offering'], scheduled_at=timezone.now()).id}/").status_code == 405
    inquiry = Inquiry.objects.create(lead=lead, listing=catalog["listing"], channel="MANUAL")
    assert admin_client.delete(f"/api/v1/admin/inquiries/{inquiry.id}/").status_code == 405


@pytest.mark.django_db
def test_visit_update_rolls_back_other_fields_when_status_transition_is_invalid(admin_client, catalog):
    monday = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
    tuesday = monday + timedelta(days=1)
    lead = Lead.objects.create(first_name="Visita atómica")
    visit = Visit.objects.create(
        lead=lead, offering=catalog["offering"], scheduled_at=monday,
        status=Visit.Status.COMPLETED, completed_at=monday,
    )
    response = admin_client.patch(
        f"/api/v1/admin/visits/{visit.id}/",
        {"scheduled_at": tuesday.isoformat(), "status": Visit.Status.CANCELLED},
        format="json",
    )
    assert response.status_code == 400
    visit.refresh_from_db()
    assert visit.scheduled_at == monday
    assert visit.status == Visit.Status.COMPLETED
