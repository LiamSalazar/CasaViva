import pytest
from io import StringIO
from unittest.mock import patch
from django.core.management.base import CommandError
from django.core.management import call_command
from django.test import override_settings
from django.db import connection
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.exceptions import ValidationError

from apps.content.models import AboutContent, SiteSettings
from apps.audit.models import AuditEvent
from apps.crm.models import ConsentRecord, PrivacyNoticeVersion, TermsOfUseVersion
from apps.crm.legal_services import find_unresolved_legal_placeholders
from apps.common.antibot import verify_antibot


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
    response = admin_client.patch(f"/api/v1/admin/{path}/{draft.id}/", {"title": "Documento", "body": "Contenido completo", "effective_at": timezone.now().isoformat(), "production_ready": True}, format="json")
    assert response.status_code == 200
    published = admin_client.post(f"/api/v1/admin/{path}/{draft.id}/publish/", {}, format="json")
    assert published.status_code == 200
    assert len(published.data["content_hash"]) == 64
    assert admin_client.patch(f"/api/v1/admin/{path}/{draft.id}/", {"body": "Cambio"}, format="json").status_code == 400
    assert model.objects.filter(is_active=True).count() == 1
    assert AuditEvent.objects.filter(action="LEGAL_DOCUMENT_PUBLISHED", entity_id=str(draft.id)).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("path,model", [("privacy-notices", PrivacyNoticeVersion), ("terms-of-use", TermsOfUseVersion)])
def test_cannot_publish_not_production_ready_and_previous_remains_active(admin_client, path, model):
    previous = model.objects.create(
        version="active-ready", title="Vigente", body="Contenido vigente", status="PUBLISHED",
        production_ready=True, is_active=True, effective_at=timezone.now(), published_at=timezone.now(),
    )
    draft = model.objects.create(version="draft-not-ready", title="Borrador", body="Contenido completo")

    response = admin_client.post(f"/api/v1/admin/{path}/{draft.id}/publish/", {}, format="json")

    assert response.status_code == 400
    previous.refresh_from_db(); draft.refresh_from_db()
    assert previous.status == "PUBLISHED" and previous.is_active is True
    assert draft.status == "DRAFT" and draft.is_active is False


@pytest.mark.django_db
@pytest.mark.parametrize("path,model", [("privacy-notices", PrivacyNoticeVersion), ("terms-of-use", TermsOfUseVersion)])
def test_publish_ready_version_retires_previous_atomically(admin_client, path, model):
    previous = model.objects.create(
        version="active-old", title="Anterior", body="Contenido anterior", status="PUBLISHED",
        production_ready=True, is_active=True, effective_at=timezone.now(), published_at=timezone.now(),
    )
    draft = model.objects.create(version="ready-next", title="Nueva", body="Contenido integral", production_ready=True)

    response = admin_client.post(f"/api/v1/admin/{path}/{draft.id}/publish/", {}, format="json")

    assert response.status_code == 200
    previous.refresh_from_db(); draft.refresh_from_db()
    assert previous.status == "RETIRED" and previous.is_active is False
    assert draft.status == "PUBLISHED" and draft.is_active is True
    with pytest.raises(ValueError):
        draft.body = "Mutación prohibida"
        draft.save()


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


@pytest.mark.django_db
@override_settings(
    DEBUG=False,
    SECRET_KEY="readiness-test-secret-that-is-longer-than-thirty-two-characters",
    ALLOWED_HOSTS=["pilot.example.test"],
    CSRF_TRUSTED_ORIGINS=["https://pilot.example.test"],
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_SSL_REDIRECT=True,
    STORAGE_BACKEND="s3",
    ANTIBOT_ENABLED=False,
    LEAD_NOTIFICATION_BACKEND="disabled",
)
def test_first_install_readiness_fails_then_passes(owner, monkeypatch):
    if connection.vendor == "postgresql" and connection.settings_dict.get("USER") != "casaviva_app":
        pytest.skip("The PostgreSQL pytest database is administered by its test-creation role; runtime role is rehearsed separately.")
    env = {
        "PUBLIC_DOMAIN": "pilot.example.test", "ACME_EMAIL": "ops@example.test",
        "S3_BUCKET_NAME": "private-media", "MEDIA_REMOTE_HOSTNAME": "media.example.test",
        "APP_DATABASE_URL": "postgresql://casaviva_app:app@postgres/casaviva",
        "MIGRATOR_DATABASE_URL": "postgresql://casaviva_migrator:migrate@postgres/casaviva",
        "BACKUP_DATABASE_URL": "postgresql://casaviva_backup:backup@postgres/casaviva",
        "BACKUP_S3_URI": "s3://private-backups/daily",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(CommandError):
        call_command("check_production_readiness")

    SiteSettings.objects.update_or_create(key="main", defaults={
        "brand_name": "CasaViva", "responsible_name": "José Alfredo Salazar Hernández",
        "operator_type": "PERSONA_FISICA", "commercial_role": "EXTERNAL_PROMOTER",
        "responsible_address": "Domicilio configurado por el responsable",
        "privacy_email": "privacy@example.test", "contact_email": "contact@example.test",
        "contact_phone": "+52 55 0000 0000",
    })
    for model, version in ((PrivacyNoticeVersion, "integral-ready"), (TermsOfUseVersion, "terms-ready")):
        model.objects.create(version=version, title="Documento integral", body="Contenido legal completo", status="PUBLISHED", is_active=True, production_ready=True, effective_at=timezone.now(), published_at=timezone.now())
    TOTPDevice.objects.create(user=owner, name="readiness", confirmed=True)
    output = StringIO()
    call_command("check_production_readiness", stdout=output)
    assert "PASS" in output.getvalue()


@pytest.mark.parametrize(
    "enabled,token,test_token,raises",
    [(False, "", "", False), (True, "valid-test-token", "valid-test-token", False), (True, "", "valid-test-token", True), (True, "invalid", "valid-test-token", True)],
)
def test_turnstile_disabled_valid_invalid_and_missing(enabled, token, test_token, raises):
    with override_settings(ANTIBOT_ENABLED=enabled, ANTIBOT_PROVIDER="turnstile", TURNSTILE_SECRET_KEY="secret", TURNSTILE_TEST_TOKEN=test_token):
        if raises:
            with patch("apps.common.antibot.urlopen", side_effect=OSError("no network")), pytest.raises(ValidationError):
                verify_antibot(token)
        else:
            verify_antibot(token)
