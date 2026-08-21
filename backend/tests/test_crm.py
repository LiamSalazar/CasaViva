from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

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
