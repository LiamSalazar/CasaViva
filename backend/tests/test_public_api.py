import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_public_listing_visibility_and_no_internal_leak(client, catalog):
    response = client.get("/api/v1/public/listings/casa-modelo/")
    assert response.status_code == 200
    body = response.json()
    for forbidden in ["internal_notes", "internal_reference", "default_commission_rate", "created_by", "updated_by", "permissions"]:
        assert forbidden not in body

    listing = catalog["listing"]
    listing.is_published = False
    listing.save()
    assert client.get("/api/v1/public/listings/casa-modelo/").status_code == 404
    listing.is_published = True
    listing.archived_at = timezone.now()
    listing.save()
    assert client.get("/api/v1/public/listings/casa-modelo/").status_code == 404


@pytest.mark.django_db
def test_public_inquiry_deduplicates_exact_email(client, catalog):
    payload = {"first_name": "Persona", "email": "PERSONA@example.test", "message": "Información", "listing_slug": "casa-modelo", "privacy_consent": True}
    assert client.post("/api/v1/public/inquiries/", payload, content_type="application/json").status_code == 201
    assert client.post("/api/v1/public/inquiries/", payload, content_type="application/json").status_code == 201
    from apps.crm.models import Lead, Inquiry
    assert Lead.objects.count() == 1
    assert Inquiry.objects.count() == 2


@pytest.mark.django_db
def test_hard_delete_unknown_listing_returns_404(admin_client):
    response = admin_client.post(
        "/api/v1/admin/listings/00000000-0000-0000-0000-000000000000/hard-delete/",
        {"confirmation": "Inexistente", "reason": "Prueba"},
        format="json",
    )
    assert response.status_code == 404
