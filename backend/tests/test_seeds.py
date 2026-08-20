import pytest
from django.core.management import call_command
from apps.catalog.models import Developer, Development, HousingModel, PropertyOffering
from apps.listings.models import Listing, PriceRecord


@pytest.mark.django_db
def test_reference_seed_is_idempotent_and_keeps_unknowns_null():
    call_command("seed_system")
    call_command("seed_reference_catalog")
    counts = (Developer.all_objects.count(), Development.all_objects.count(), HousingModel.all_objects.count(), PropertyOffering.all_objects.count(), Listing.all_objects.count(), PriceRecord.objects.count())
    call_command("seed_reference_catalog")
    assert counts == (Developer.all_objects.count(), Development.all_objects.count(), HousingModel.all_objects.count(), PropertyOffering.all_objects.count(), Listing.all_objects.count(), PriceRecord.objects.count())
    bosques = Development.all_objects.get(name="Bosques de Ibiza")
    assert not bosques.is_published
    assert not PropertyOffering.all_objects.filter(development_model__development=bosques).exists()
