import pytest
from django.core.management import call_command
from apps.catalog.models import Developer, Development, HousingModel, PropertyOffering
from apps.listings.models import Listing, PriceRecord
from apps.content.models import LocationContent


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
    assert LocationContent.objects.filter(is_featured=True).exists()


@pytest.mark.django_db
def test_reference_seed_does_not_overwrite_human_corrections():
    call_command("seed_system")
    call_command("seed_reference_catalog")
    listing = Listing.objects.filter(is_published=True).first()
    listing.title = "Corrección humana"
    listing.save(update_fields=["title", "updated_at"])
    current_price = listing.offering.prices.get(effective_to__isnull=True)
    current_price.amount_min = 987654
    current_price.save(update_fields=["amount_min", "updated_at"])
    call_command("seed_reference_catalog")
    listing.refresh_from_db()
    current_price.refresh_from_db()
    assert listing.title == "Corrección humana"
    assert current_price.amount_min == 987654
