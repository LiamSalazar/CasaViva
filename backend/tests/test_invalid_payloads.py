import pytest

from apps.catalog.models import PropertyOffering
from apps.listings.models import Listing


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query",
    [
        "developer=not-a-uuid",
        "development=not-a-uuid",
        "condition=WHATEVER",
        "source_type=WHATEVER",
        "price_min=not-a-number",
        "price_min=-1",
        "price_min=200&price_max=100",
        "bedrooms_min=-2",
        "ordering=random-score",
    ],
)
def test_invalid_public_filters_never_raise_500(client, catalog, query):
    response = client.get(f"/api/v1/public/listings/?{query}")
    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutation",
    [
        {"offering": None},
        {"offering": {"property_type": "not-a-uuid"}},
        {"listing": None},
        {"availability": {"status": "WHATEVER"}},
        {"price": {"price_type": "WHATEVER"}},
        {"media": [{"media_id": "not-a-uuid", "role": "HERO"}]},
    ],
)
def test_invalid_property_aggregate_payloads_return_400_without_residue(admin_client, mutation):
    before = (PropertyOffering.all_objects.count(), Listing.all_objects.count())
    payload = {
        "offering": {}, "listing": {"title": "Inválida", "slug": "invalida"},
        "price": {"price_type": "ON_REQUEST"}, "availability": {"status": "AVAILABLE"},
    }
    payload.update(mutation)
    response = admin_client.post("/api/v1/admin/properties/", payload, format="json")
    assert response.status_code == 400
    assert (PropertyOffering.all_objects.count(), Listing.all_objects.count()) == before


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("developers", {"name": "No", "version": "not-a-number"}),
        ("content", {"hero_title": "No", "version": []}),
        ("leads", {"first_name": "No", "version": "NaN"}),
    ],
)
def test_invalid_optimistic_versions_return_400_not_500(admin_client, catalog, path, payload):
    if path == "developers":
        identifier = catalog["developer"].id
    elif path == "leads":
        from apps.crm.models import Lead
        identifier = Lead.objects.create(first_name="Versión").id
    else:
        from apps.content.models import HomeContent
        identifier = HomeContent.objects.create(key="versions").id
    response = admin_client.patch(f"/api/v1/admin/{path}/{identifier}/", payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_hard_delete_rejects_malformed_confirmation_payload(admin_client, catalog):
    listing = catalog["listing"]
    admin_client.delete(f"/api/v1/admin/properties/{listing.id}/")
    response = admin_client.post(
        f"/api/v1/admin/properties/{listing.id}/hard-delete/",
        {"confirmation": [], "reason": {"unexpected": "object"}},
        format="json",
    )
    assert response.status_code == 400
    assert Listing.all_objects.filter(pk=listing.pk).exists()
