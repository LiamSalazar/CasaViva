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
