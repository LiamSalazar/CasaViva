import pytest
from django.core.management import call_command
from django.utils import timezone


@pytest.mark.django_db
def test_public_listing_visibility_and_no_internal_leak(client, catalog):
    response = client.get("/api/v1/public/listings/casa-modelo/")
    assert response.status_code == 200
    body = response.json()
    for forbidden in ["internal_notes", "internal_reference", "default_commission_rate", "created_by", "updated_by", "permissions"]:
        assert forbidden not in body
    assert set(body) == {
        "id", "slug", "title", "propertyType", "propertyTypeName", "sourceType", "condition",
        "status", "published", "featured", "price", "priceMax", "currency", "priceLabel",
        "state", "municipality", "neighborhood", "latitude", "longitude", "bedrooms",
        "bathrooms", "fullBathrooms", "halfBathrooms", "parkingSpaces", "constructionM2",
        "constructionAreaBasis", "landM2", "landAreaBasis", "gardenM2", "shortDescription",
        "description", "amenities", "amenitySlugs", "developerId", "developerName",
        "developmentId", "developmentName", "modelName", "heroImage", "gallery", "floorplans",
        "providerLabel", "promotionRole", "informationVerifiedAt", "promotion", "createdAt", "updatedAt",
    }

    listing = catalog["listing"]
    listing.is_published = False
    listing.save()
    assert client.get("/api/v1/public/listings/casa-modelo/").status_code == 404
    listing.is_published = True
    listing.archived_at = timezone.now()
    listing.save()
    assert client.get("/api/v1/public/listings/casa-modelo/").status_code == 404


@pytest.mark.django_db
def test_public_development_without_media_keeps_gallery_empty(client, catalog):
    development = catalog["development"]
    development.is_published = True
    development.save(update_fields=["is_published", "updated_at"])
    response = client.get(f"/api/v1/public/developments/{development.slug}/")
    assert response.status_code == 200
    assert response.data["heroImage"] is None
    assert response.data["gallery"] == []


@pytest.mark.django_db
def test_public_inquiry_deduplicates_exact_email(client, catalog):
    call_command("seed_system")
    payload = {"first_name": "Persona", "email": "PERSONA@example.test", "message": "Información", "listing_slug": "casa-modelo", "privacy_consent": True, "transfer_consent": True}
    assert client.post("/api/v1/public/inquiries/", payload, content_type="application/json").status_code == 201
    assert client.post("/api/v1/public/inquiries/", payload, content_type="application/json").status_code == 201
    from apps.crm.models import Lead, Inquiry
    assert Lead.objects.count() == 1
    assert Inquiry.objects.count() == 2


@pytest.mark.django_db
def test_hard_delete_unknown_listing_returns_404(admin_client):
    response = admin_client.post(
        "/api/v1/admin/properties/00000000-0000-0000-0000-000000000000/hard-delete/",
        {"confirmation": "Inexistente", "reason": "Prueba"},
        format="json",
    )
    assert response.status_code == 404
