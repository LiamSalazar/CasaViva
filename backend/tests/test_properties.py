from copy import deepcopy
from decimal import Decimal

import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone

from apps.catalog.models import Amenity, PropertyOffering, PropertyType
from apps.listings.models import AvailabilityRecord, Listing, PriceRecord, SlugRedirect
from apps.analytics.models import AnalyticsEvent, AnonymousVisitor, WebSession
from apps.audit.models import AuditEvent


def aggregate_payload(catalog, **overrides):
    payload = {
        "offering": {
            "source_type": "PRIVATE",
            "promotion_authorized": True,
            "information_verified_at": timezone.now().isoformat(),
            "condition": "NEW",
            "development_model": None,
            "property_type": str(catalog["offering"].property_type_id),
            "state": str(catalog["state"].id),
            "municipality": str(catalog["municipality"].id),
            "street_address": "Calle Prueba 42",
            "postal_code": "55740",
            "latitude": "19.601234",
            "longitude": "-99.010234",
            "bedrooms_min": "2.0",
            "bedrooms_max": "3.0",
            "bathrooms_total": "1.5",
            "full_bathrooms": 1,
            "half_bathrooms": 1,
            "parking_min": 1,
            "parking_max": 2,
            "levels_min": 2,
            "levels_max": 3,
            "construction_area_min": "70.00",
            "construction_area_max": "85.00",
            "construction_area_basis": "RANGE",
            "land_area_min": "90.00",
            "land_area_basis": "EXACT",
            "garden_area_min": "12.00",
            "garden_area_max": "18.00",
            "garden_area_basis": "RANGE",
            "default_commission_rate": "4.50",
            "internal_reference": "CV-ROUNDTRIP",
            "internal_notes": "Sólo administración",
            "amenity_ids": [],
            "feature_values_input": [],
        },
        "listing": {
            "title": "Casa de prueba integral",
            "slug": "casa-prueba-integral",
            "short_description": "Descripción breve",
            "description": "Descripción completa",
            "is_featured": True,
        },
        "price": {"price_type": "RANGE", "amount_min": "1000000.00", "amount_max": "1200000.00", "currency": "MXN"},
        "availability": {"status": "AVAILABLE"},
        "published": True,
        "media": [],
    }
    for key, value in overrides.items():
        payload[key] = value
    return payload


@pytest.mark.django_db
def test_property_aggregate_round_trip_including_condition_geo_levels_and_amenities(admin_client, catalog):
    duplex = PropertyType.objects.create(code="duplex", name="Dúplex")
    amenity = Amenity.objects.create(name="Salón de eventos", slug="salon-eventos", category="DEVELOPMENT")
    payload = aggregate_payload(catalog)
    payload["offering"]["property_type"] = str(duplex.id)
    payload["offering"]["amenity_ids"] = [str(amenity.id)]

    response = admin_client.post("/api/v1/admin/properties/", payload, format="json")
    assert response.status_code == 201, response.data
    listing = Listing.objects.get(slug="casa-prueba-integral")
    offering = listing.offering
    assert offering.source_type == "PRIVATE"
    assert offering.condition == "NEW"  # PRIVATE + NEW is deliberately valid.
    assert offering.street_address == "Calle Prueba 42"
    assert offering.postal_code == "55740"
    assert offering.latitude == Decimal("19.601234")
    assert offering.longitude == Decimal("-99.010234")
    assert offering.levels_min == 2 and offering.levels_max == 3
    assert offering.full_bathrooms == 1 and offering.half_bathrooms == 1
    assert offering.garden_area_min == Decimal("12.00")
    assert offering.garden_area_max == Decimal("18.00")
    assert offering.garden_area_basis == "RANGE"
    assert list(offering.amenities.values_list("name", flat=True)) == ["Salón de eventos"]
    assert listing.is_published is True

    public = admin_client.get("/api/v1/public/listings/casa-prueba-integral/")
    assert public.status_code == 200
    assert public.data["condition"] == "new"
    assert public.data["fullBathrooms"] == 1
    assert public.data["propertyType"] == "duplex"
    assert public.data["amenities"] == ["Salón de eventos"]


@pytest.mark.django_db
def test_property_create_rolls_back_when_price_is_invalid(admin_client, catalog):
    before = (PropertyOffering.all_objects.count(), Listing.all_objects.count(), PriceRecord.objects.count(), AvailabilityRecord.objects.count())
    payload = aggregate_payload(catalog)
    payload["price"] = {"price_type": "RANGE", "amount_min": "1200000", "amount_max": "1000000"}
    response = admin_client.post("/api/v1/admin/properties/", payload, format="json")
    assert response.status_code == 400
    assert (PropertyOffering.all_objects.count(), Listing.all_objects.count(), PriceRecord.objects.count(), AvailabilityRecord.objects.count()) == before


@pytest.mark.django_db
def test_property_update_is_atomic_and_does_not_add_unchanged_history(admin_client, catalog):
    create = admin_client.post("/api/v1/admin/properties/", aggregate_payload(catalog), format="json")
    assert create.status_code == 201, create.data
    listing = Listing.objects.get(slug="casa-prueba-integral")
    original_description = listing.description
    price_count = PriceRecord.objects.filter(offering=listing.offering).count()
    availability_count = AvailabilityRecord.objects.filter(offering=listing.offering).count()

    payload = aggregate_payload(catalog)
    payload.update({"listing_version": listing.version, "offering_version": listing.offering.version})
    payload["listing"]["description"] = "No debe persistir"
    payload["price"] = {"price_type": "RANGE", "amount_min": "200", "amount_max": "100"}
    invalid = admin_client.patch(f"/api/v1/admin/properties/{listing.id}/", payload, format="json")
    assert invalid.status_code == 400
    listing.refresh_from_db()
    assert listing.description == original_description

    payload["price"] = {"price_type": "RANGE", "amount_min": "1000000.00", "amount_max": "1200000.00", "currency": "MXN"}
    valid = admin_client.patch(f"/api/v1/admin/properties/{listing.id}/", payload, format="json")
    assert valid.status_code == 200, valid.data
    assert PriceRecord.objects.filter(offering=listing.offering).count() == price_count
    assert AvailabilityRecord.objects.filter(offering=listing.offering).count() == availability_count


@pytest.mark.django_db
def test_published_property_cannot_become_unauthorized(admin_client, catalog):
    listing = catalog["listing"]
    payload = aggregate_payload(catalog)
    payload.update({"listing_version": listing.version, "offering_version": listing.offering.version})
    payload["offering"]["source_type"] = "DEVELOPER"
    payload["offering"]["development_model"] = str(catalog["link"].id)
    payload["offering"]["promotion_authorized"] = False
    response = admin_client.patch(f"/api/v1/admin/properties/{listing.id}/", payload, format="json")
    assert response.status_code == 400
    listing.offering.refresh_from_db()
    assert listing.offering.promotion_authorized is True


@pytest.mark.django_db
def test_published_property_cannot_lose_verified_at(admin_client, catalog):
    listing = catalog["listing"]
    payload = aggregate_payload(catalog)
    payload.update({"listing_version": listing.version, "offering_version": listing.offering.version})
    payload["offering"]["source_type"] = "DEVELOPER"
    payload["offering"]["development_model"] = str(catalog["link"].id)
    payload["offering"]["information_verified_at"] = None
    response = admin_client.patch(f"/api/v1/admin/properties/{listing.id}/", payload, format="json")
    assert response.status_code == 400
    listing.offering.refresh_from_db()
    assert listing.offering.information_verified_at is not None


@pytest.mark.django_db
def test_stale_property_versions_return_409_without_partial_changes(admin_client, catalog):
    created = admin_client.post("/api/v1/admin/properties/", aggregate_payload(catalog), format="json")
    listing = Listing.objects.get(pk=created.data["id"])
    payload = aggregate_payload(catalog)
    payload.update({"listing_version": listing.version - 1, "offering_version": listing.offering.version})
    payload["listing"]["description"] = "Intento obsoleto"
    response = admin_client.patch(f"/api/v1/admin/properties/{listing.id}/", payload, format="json")
    assert response.status_code == 409
    listing.refresh_from_db()
    assert listing.description != "Intento obsoleto"


@pytest.mark.django_db
def test_slug_update_creates_real_permanent_redirect(admin_client, catalog):
    created = admin_client.post("/api/v1/admin/properties/", aggregate_payload(catalog), format="json")
    listing = Listing.objects.get(pk=created.data["id"])
    payload = aggregate_payload(catalog)
    payload.update({"listing_version": listing.version, "offering_version": listing.offering.version})
    payload["listing"]["slug"] = "casa-prueba-renombrada"
    response = admin_client.patch(f"/api/v1/admin/properties/{listing.id}/", payload, format="json")
    assert response.status_code == 200, response.data
    assert SlugRedirect.objects.filter(old_path="/propiedades/casa-prueba-integral", new_path="/propiedades/casa-prueba-renombrada").exists()
    redirect = admin_client.get("/api/v1/redirect/propiedades/casa-prueba-integral/")
    assert redirect.status_code == 301
    assert redirect["Location"] == "/propiedades/casa-prueba-renombrada"


@pytest.mark.django_db
def test_public_listing_query_count_does_not_grow_linearly(client, catalog):
    def measured():
        with CaptureQueriesContext(connection) as captured:
            response = client.get("/api/v1/public/listings/?page_size=25")
            assert response.status_code == 200
            list(response.data["results"])
        return len(captured)

    one_count = measured()
    base = catalog["listing"]
    for index in range(24):
        offering = PropertyOffering.objects.create(
            source_type="DEVELOPER", condition="NEW", development_model=catalog["link"],
            property_type=catalog["offering"].property_type,
        )
        PriceRecord.objects.create(offering=offering, price_type="FROM", amount_min=1_000_000 + index, effective_from=timezone.now())
        AvailabilityRecord.objects.create(offering=offering, status="AVAILABLE", effective_from=timezone.now())
        Listing.objects.create(offering=offering, title=f"Casa {index}", slug=f"casa-query-{index}", is_published=True, published_at=timezone.now())
    many_count = measured()
    assert many_count <= one_count + 1, (one_count, many_count)


@pytest.mark.django_db
def test_aggregate_hard_delete_keeps_analytics_snapshot_and_audit(admin_client, catalog):
    listing = catalog["listing"]
    visitor = AnonymousVisitor.objects.create(first_seen_at=timezone.now(), last_seen_at=timezone.now())
    session = WebSession.objects.create(visitor=visitor, started_at=timezone.now(), last_seen_at=timezone.now(), landing_path="/", consent_state="ESSENTIAL")
    event = AnalyticsEvent.objects.create(
        occurred_at=timezone.now(), event_name="listing_viewed", visitor=visitor,
        session=session, listing=listing, offering=listing.offering,
    )
    assert admin_client.delete(f"/api/v1/admin/properties/{listing.id}/").status_code == 204
    response = admin_client.post(
        f"/api/v1/admin/properties/{listing.id}/hard-delete/",
        {"confirmation": listing.title, "reason": "Carga errónea de prueba"}, format="json",
    )
    assert response.status_code == 204, response.data
    event.refresh_from_db()
    assert event.listing_id is None and event.offering_id is None
    assert event.listing_public_key == listing.id
    assert event.listing_title_snapshot == listing.title
    assert AuditEvent.objects.filter(action="HARD_DELETE", entity_id=str(listing.id)).exists()
