from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.catalog.models import (
    Amenity,
    Developer,
    FeatureChoice,
    FeatureDefinition,
    OfferingFeatureValue,
    PropertyOffering,
)
from apps.listings.models import AvailabilityRecord, ListingMedia, PriceRecord, SlugRedirect
from apps.media_library.models import MediaAsset


pytestmark = pytest.mark.django_db


def test_business_and_editable_catalog_endpoints_round_trip(admin_client, catalog):
    created = admin_client.post(
        "/api/v1/admin/developers/",
        {"name": "Nueva desarrolladora", "slug": "nueva-desarrolladora", "is_active": True},
        format="json",
    )
    assert created.status_code == 201
    developer_id = created.data["id"]

    stale = admin_client.patch(
        f"/api/v1/admin/developers/{developer_id}/",
        {"name": "No debe guardarse", "version": 0},
        format="json",
    )
    assert stale.status_code == 409

    updated = admin_client.patch(
        f"/api/v1/admin/developers/{developer_id}/",
        {"name": "Desarrolladora corregida", "version": created.data["version"]},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["name"] == "Desarrolladora corregida"

    assert admin_client.delete(f"/api/v1/admin/developers/{developer_id}/").status_code == 204
    archived = admin_client.get("/api/v1/admin/developers/?archived=all")
    assert developer_id in {str(item["id"]) for item in archived.data["results"]}
    restored = admin_client.post(f"/api/v1/admin/developers/{developer_id}/restore/", {}, format="json")
    assert restored.status_code == 200
    assert restored.data["archived_at"] is None

    property_type = admin_client.post(
        "/api/v1/admin/property-types/",
        {"code": "duplex", "name": "Dúplex", "is_active": True, "sort_order": 8},
        format="json",
    )
    assert property_type.status_code == 201
    renamed_type = admin_client.patch(
        f"/api/v1/admin/property-types/{property_type.data['id']}/",
        {"name": "Dúplex residencial"},
        format="json",
    )
    assert renamed_type.status_code == 200
    assert renamed_type.data["name"] == "Dúplex residencial"
    assert admin_client.delete(f"/api/v1/admin/property-types/{property_type.data['id']}/").status_code == 204
    inactive = admin_client.get("/api/v1/admin/property-types/?is_active=false")
    assert property_type.data["id"] in {str(item["id"]) for item in inactive.data["results"]}

    amenity = admin_client.post(
        "/api/v1/admin/amenities/",
        {"name": "Bodega", "slug": "bodega", "category": "INTERIOR", "is_active": True},
        format="json",
    )
    assert amenity.status_code == 201
    feature = admin_client.post(
        "/api/v1/admin/features/",
        {
            "code": "roof-garden",
            "label": "Roof garden",
            "category": "Exterior",
            "data_type": "BOOLEAN",
            "is_public": True,
            "is_filterable": True,
            "is_active": True,
        },
        format="json",
    )
    assert feature.status_code == 201
    assert AuditEvent.objects.filter(action="CREATE").exists()

    development = catalog["development"]
    old_slug = development.slug
    changed = admin_client.patch(
        f"/api/v1/admin/developments/{development.id}/",
        {"slug": "desarrollo-renombrado", "version": development.version},
        format="json",
    )
    assert changed.status_code == 200
    assert SlugRedirect.objects.filter(
        old_path=f"/desarrollos/{old_slug}", new_path="/desarrollos/desarrollo-renombrado"
    ).exists()


def test_offering_amenities_and_typed_features_round_trip(admin_client, catalog):
    amenity_a = Amenity.objects.create(name="Balcón", slug="balcon", category="EXTERIOR")
    amenity_b = Amenity.objects.create(name="Bodega", slug="bodega-2", category="INTERIOR")
    boolean = FeatureDefinition.objects.create(
        code="roof", label="Roof garden", category="Exterior", data_type="BOOLEAN"
    )
    number = FeatureDefinition.objects.create(
        code="front", label="Frente", category="Medidas", data_type="NUMBER", unit="m"
    )
    text = FeatureDefinition.objects.create(
        code="laundry", label="Lavandería", category="Interior", data_type="TEXT"
    )
    choice = FeatureDefinition.objects.create(
        code="view", label="Vista", category="Exterior", data_type="CHOICE"
    )
    option = FeatureChoice.objects.create(definition=choice, value="garden", label="Jardín")

    payload = {
        "source_type": "PRIVATE",
        "condition": "NEW",
        "property_type": str(catalog["offering"].property_type_id),
        "state": str(catalog["state"].id),
        "municipality": str(catalog["municipality"].id),
        "internal_reference": "CV-TYPED-1",
        "amenity_ids": [str(amenity_a.id), str(amenity_b.id)],
        "feature_values_input": [
            {"definition": str(boolean.id), "value_boolean": True},
            {"definition": str(number.id), "value_number": "8.250"},
            {"definition": str(text.id), "value_text": "Cuarto independiente"},
            {"definition": str(choice.id), "value_choice": str(option.id)},
        ],
    }
    created = admin_client.post("/api/v1/admin/offerings/", payload, format="json")
    assert created.status_code == 201, created.data
    offering_id = created.data["id"]
    offering = PropertyOffering.objects.get(pk=offering_id)
    assert set(offering.amenities.values_list("id", flat=True)) == {amenity_a.id, amenity_b.id}
    assert OfferingFeatureValue.objects.filter(offering=offering).count() == 4

    fetched = admin_client.get(f"/api/v1/admin/offerings/{offering_id}/")
    assert fetched.status_code == 200
    assert {item["definition"] for item in fetched.data["feature_values"]} == {
        str(boolean.id), str(number.id), str(text.id), str(choice.id)
    }

    updated = admin_client.patch(
        f"/api/v1/admin/offerings/{offering_id}/",
        {
            "version": created.data["version"],
            "amenity_ids": [str(amenity_b.id)],
            "feature_values_input": [
                {"definition": str(boolean.id), "value_boolean": False},
                {"definition": str(text.id), "value_text": ""},
            ],
        },
        format="json",
    )
    assert updated.status_code == 200, updated.data
    offering.refresh_from_db()
    assert list(offering.amenities.values_list("id", flat=True)) == [amenity_b.id]
    values = OfferingFeatureValue.objects.filter(offering=offering)
    assert values.count() == 1
    assert values.get().value_boolean is False


def test_invalid_typed_feature_rolls_back_entire_offering(admin_client, catalog):
    feature = FeatureDefinition.objects.create(
        code="orientation", label="Orientación", category="Exterior", data_type="CHOICE"
    )
    other = FeatureDefinition.objects.create(
        code="finish", label="Acabado", category="Interior", data_type="CHOICE"
    )
    wrong_option = FeatureChoice.objects.create(definition=other, value="wood", label="Madera")
    count_before = PropertyOffering.objects.count()

    response = admin_client.post(
        "/api/v1/admin/offerings/",
        {
            "source_type": "PRIVATE",
            "condition": "USED",
            "property_type": str(catalog["offering"].property_type_id),
            "internal_reference": "NO-DEBE-EXISTIR",
            "feature_values_input": [
                {"definition": str(feature.id), "value_choice": str(wrong_option.id)}
            ],
        },
        format="json",
    )
    assert response.status_code == 400
    assert PropertyOffering.objects.count() == count_before
    assert not PropertyOffering.objects.filter(internal_reference="NO-DEBE-EXISTIR").exists()


def test_listing_history_media_archive_restore_and_export(admin_client, owner, catalog):
    listing = catalog["listing"]
    now = timezone.now() + timedelta(minutes=1)
    price = admin_client.post(
        f"/api/v1/admin/properties/{listing.id}/price/",
        {
            "price_type": "RANGE",
            "amount_min": "1300000.00",
            "amount_max": "1450000.00",
            "effective_from": now.isoformat(),
            "observations": "Lista de agosto",
        },
        format="json",
    )
    assert price.status_code == 201, price.data
    history = admin_client.get(f"/api/v1/admin/properties/{listing.id}/price_history/")
    assert history.status_code == 200
    assert len(history.data) == 2
    assert PriceRecord.objects.filter(offering=listing.offering, effective_to__isnull=True).count() == 1

    availability = admin_client.post(
        f"/api/v1/admin/properties/{listing.id}/availability/",
        {"status": "RESERVED", "notes": "Apartada por cliente"},
        format="json",
    )
    assert availability.status_code == 201
    availability_history = admin_client.get(
        f"/api/v1/admin/properties/{listing.id}/availability_history/"
    )
    assert len(availability_history.data) == 2
    assert AvailabilityRecord.objects.filter(
        offering=listing.offering, effective_to__isnull=True
    ).count() == 1

    first = MediaAsset.objects.create(
        storage_key="tests/first.jpg", media_type="IMAGE", original_filename="first.jpg",
        mime_type="image/jpeg", byte_size=10, sha256="1" * 64, uploaded_by=owner,
    )
    second = MediaAsset.objects.create(
        storage_key="tests/second.jpg", media_type="IMAGE", original_filename="second.jpg",
        mime_type="image/jpeg", byte_size=11, sha256="2" * 64, uploaded_by=owner,
    )
    invalid_role = admin_client.post(
        f"/api/v1/admin/properties/{listing.id}/media/",
        {"media_id": str(first.id), "role": "INVALID"}, format="json",
    )
    assert invalid_role.status_code == 400
    for asset in (first, second):
        response = admin_client.post(
            f"/api/v1/admin/properties/{listing.id}/media/",
            {"media_id": str(asset.id), "role": "HERO"}, format="json",
        )
        assert response.status_code == 201
    assert ListingMedia.objects.filter(listing=listing, role="HERO").count() == 1
    assert ListingMedia.objects.get(listing=listing, role="HERO").media == second

    exported = admin_client.get("/api/v1/admin/offerings/export/")
    assert exported.status_code == 200
    assert exported["Content-Type"].startswith("text/csv")
    assert "Propiedades" not in exported.content.decode("utf-8")  # encabezados, no título decorativo

    preview = admin_client.get(f"/api/v1/admin/properties/{listing.id}/delete-preview/")
    assert preview.status_code == 200
    assert preview.data["can_delete"] is False
    assert admin_client.delete(f"/api/v1/admin/properties/{listing.id}/").status_code == 204
    listing.refresh_from_db()
    assert listing.archived_at is not None
    assert listing.is_published is False
    restored = admin_client.post(f"/api/v1/admin/properties/{listing.id}/restore/", {}, format="json")
    assert restored.status_code == 200
    listing.refresh_from_db()
    assert listing.archived_at is None


def test_public_home_and_legacy_listing_mutation_is_blocked(admin_client, client, catalog):
    home = client.get("/api/v1/public/home/")
    assert home.status_code == 200
    assert home.data["featured_listings"][0]["slug"] == catalog["listing"].slug

    listing = catalog["listing"]
    response = admin_client.patch(
        f"/api/v1/admin/listings/{listing.id}/",
        {"slug": "casa-con-url-nueva", "version": listing.version},
        format="json",
    )
    assert response.status_code == 405
    listing.refresh_from_db()
    assert listing.slug == "casa-modelo"
