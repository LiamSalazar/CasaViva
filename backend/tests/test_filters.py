import pytest
from django.utils import timezone

from apps.catalog.models import Amenity, PropertyOffering, PropertyType
from apps.listings.models import AvailabilityRecord, Listing, PriceRecord


def slugs(response):
    return [row["slug"] for row in response.data["results"]]


@pytest.mark.django_db
def test_public_search_options_are_dynamic(client):
    duplex = PropertyType.objects.create(code="duplex", name="Dúplex", is_active=True)
    inactive = PropertyType.objects.create(code="inactive", name="Inactivo", is_active=False)
    amenity = Amenity.objects.create(name="Salón de eventos", slug="salon-eventos", category="DEVELOPMENT", is_active=True)
    response = client.get("/api/v1/public/search-options/")
    assert response.status_code == 200
    assert {row["code"] for row in response.data["property_types"]} >= {duplex.code}
    assert inactive.code not in {row["code"] for row in response.data["property_types"]}
    assert amenity.name in {row["name"] for row in response.data["amenities"]}


@pytest.mark.django_db
def test_public_listing_filters_cover_relations_ranges_and_all_amenities(client, catalog):
    offering = catalog["offering"]
    offering.condition = "NEW"
    offering.bedrooms_min = 2
    offering.bedrooms_max = 3
    offering.construction_area_min = 60
    offering.construction_area_max = 80
    offering.land_area_min = 70
    offering.land_area_max = 100
    offering.save()
    price = offering.prices.get(effective_to__isnull=True)
    price.price_type = "RANGE"
    price.amount_min = 1_000_000
    price.amount_max = 1_300_000
    price.save()
    garden = Amenity.objects.create(name="Jardín", slug="jardin-filter", category="EXTERIOR")
    security = Amenity.objects.create(name="Seguridad", slug="seguridad-filter", category="SERVICE")
    offering.amenities.set([garden, security])

    accepted = [
        {"state": "Estado de México"}, {"municipality": "Tecámac"},
        {"developer": str(catalog["developer"].id)}, {"development": str(catalog["development"].id)},
        {"source_type": "DEVELOPER"}, {"condition": "NEW"}, {"property_type": "house"},
        {"price_min": "1200000"}, {"price_max": "1100000"}, {"bedrooms_min": "3"},
        {"bathrooms_min": "2"}, {"construction_area": "75"}, {"land_area": "90"},
        {"amenities": "Jardín,Seguridad"}, {"query": "Casa Modelo"},
    ]
    for params in accepted:
        response = client.get("/api/v1/public/listings/", params)
        assert response.status_code == 200, params
        assert catalog["listing"].slug in slugs(response), params

    assert catalog["listing"].slug not in slugs(client.get("/api/v1/public/listings/", {"bedrooms_min": 4}))
    assert catalog["listing"].slug not in slugs(client.get("/api/v1/public/listings/", {"amenities": "Jardín,Alberca"}))


@pytest.mark.django_db
def test_sorting_keeps_on_request_prices_last_without_errors(client, catalog):
    catalog["offering"].condition = "NEW"
    catalog["offering"].save()
    on_request = PropertyOffering.objects.create(
        source_type="DEVELOPER", condition="NEW", development_model=catalog["link"], property_type=catalog["offering"].property_type,
    )
    PriceRecord.objects.create(offering=on_request, price_type="ON_REQUEST", effective_from=timezone.now())
    AvailabilityRecord.objects.create(offering=on_request, status="AVAILABLE", effective_from=timezone.now())
    Listing.objects.create(offering=on_request, title="Precio a consultar", slug="precio-a-consultar", is_published=True, published_at=timezone.now())
    for ordering in ("newest", "price_asc", "price_desc", "area_desc"):
        response = client.get("/api/v1/public/listings/", {"ordering": ordering})
        assert response.status_code == 200
        assert set(slugs(response)) == {"casa-modelo", "precio-a-consultar"}
    assert slugs(client.get("/api/v1/public/listings/", {"ordering": "price_desc"}))[-1] == "precio-a-consultar"


@pytest.mark.django_db
def test_favorites_and_similar_use_database_not_first_page(client, catalog):
    target_id = None
    for index in range(30):
        offering = PropertyOffering.objects.create(
            source_type="DEVELOPER", condition="NEW", development_model=catalog["link"], property_type=catalog["offering"].property_type,
        )
        PriceRecord.objects.create(offering=offering, price_type="FIXED", amount_min=900000 + index * 1000, effective_from=timezone.now())
        AvailabilityRecord.objects.create(offering=offering, status="AVAILABLE", effective_from=timezone.now())
        listing = Listing.objects.create(offering=offering, title=f"Inventario {index}", slug=f"inventario-{index}", is_published=True, published_at=timezone.now())
        if index == 0:
            target_id = listing.id
    first_page = client.get("/api/v1/public/listings/")
    assert str(target_id) not in {str(item["id"]) for item in first_page.data["results"]}
    favorites = client.get("/api/v1/public/listings/favorites/", {"ids": str(target_id)})
    assert favorites.status_code == 200
    assert [str(item["id"]) for item in favorites.data] == [str(target_id)]
    similar = client.get(f"/api/v1/public/listings/{catalog['listing'].slug}/similar/")
    assert similar.status_code == 200
    assert len(similar.data) == 3
    assert all(item["municipality"] == "Tecámac" and item["propertyType"] == "house" for item in similar.data)
