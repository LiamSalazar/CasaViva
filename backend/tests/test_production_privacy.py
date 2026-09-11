import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.content.models import AboutContent
from apps.crm.models import ConsentRecord, PrivacyNoticeVersion, TermsOfUseVersion
from apps.crm.legal_services import find_unresolved_legal_placeholders


@pytest.mark.django_db
def test_about_is_seeded_and_editable(admin_client):
    call_command("seed_system")
    about = AboutContent.objects.get(key="main")
    response = admin_client.patch(f"/api/v1/admin/about/{about.id}/", {"version": about.version, "hero_title": "Título editable"}, format="json")
    assert response.status_code == 200
    assert admin_client.get("/api/v1/public/about/").data["results"][0]["hero_title"] == "Título editable"


@pytest.mark.django_db
def test_property_transfer_consent_is_independent(client, catalog):
    call_command("seed_system")
    base = {"first_name": "Persona", "email": "privacy@example.test", "listing_slug": catalog["listing"].slug, "privacy_consent": True}
    assert client.post("/api/v1/public/inquiries/", base, format="json").status_code == 400
    accepted = client.post("/api/v1/public/inquiries/", {**base, "transfer_consent": True}, format="json")
    assert accepted.status_code == 201
    consents = ConsentRecord.objects.filter(lead__email="privacy@example.test")
    assert set(consents.values_list("purpose", flat=True)) == {"PRIVACY_NOTICE_ACKNOWLEDGEMENT", "LEAD_TRANSFER"}
    assert consents.values("privacy_notice_version_id").distinct().count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("path,model", [("privacy-notices", PrivacyNoticeVersion), ("terms-of-use", TermsOfUseVersion)])
def test_legal_draft_publish_hash_audit_and_immutability(admin_client, path, model):
    call_command("seed_system")
    draft = model.objects.filter(status="DRAFT").first()
    response = admin_client.patch(f"/api/v1/admin/{path}/{draft.id}/", {"title": "Documento", "body": "Contenido completo", "effective_at": timezone.now().isoformat()}, format="json")
    assert response.status_code == 200
    published = admin_client.post(f"/api/v1/admin/{path}/{draft.id}/publish/", {}, format="json")
    assert published.status_code == 200
    assert len(published.data["content_hash"]) == 64
    assert admin_client.patch(f"/api/v1/admin/{path}/{draft.id}/", {"body": "Cambio"}, format="json").status_code == 400
    assert model.objects.filter(is_active=True).count() == 1


@pytest.mark.django_db
def test_legal_placeholder_detection_allows_markdown_links():
    assert find_unresolved_legal_placeholders("Consulte [la guía](/guias/privacidad).") == []
    assert find_unresolved_legal_placeholders("Domicilio: [DOMICILIO DEL RESPONSABLE]") == ["[DOMICILIO DEL RESPONSABLE]"]


@pytest.mark.django_db
def test_public_legal_serializer_does_not_expose_admin_metadata(client):
    PrivacyNoticeVersion.objects.create(
        version="public-safe", title="Aviso", body="Contenido", status="PUBLISHED",
        is_active=True, production_ready=True, effective_at=timezone.now(), published_at=timezone.now(),
    )
    response = client.get("/api/v1/public/privacy-notice/")
    assert response.status_code == 200
    assert set(response.data) == {"version", "title", "body", "effective_at", "published_at"}
