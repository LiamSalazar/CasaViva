from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.catalog.models import PropertyOffering
from apps.listings.models import AvailabilityRecord, Listing, PriceRecord, SlugRedirect
from apps.listings.services import (
    change_availability,
    change_price,
    change_slug,
    publish_listing,
    validate_publishable,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"price_type": "WHATEVER", "amount_min": 1}, "price_type"),
        ({"price_type": "FIXED", "amount_min": "no-numérico"}, "amount_min"),
        ({"price_type": "FIXED"}, "amount_min"),
        ({"price_type": "FROM", "amount_min": -1}, "amount_min"),
        ({"price_type": "RANGE", "amount_min": 100}, "amount_max"),
        ({"price_type": "RANGE", "amount_min": 200, "amount_max": 100}, "amount_max"),
        ({"price_type": "ON_REQUEST", "amount_min": 100}, "amount_min"),
    ],
)
def test_change_price_rejects_each_invalid_domain_shape(owner, catalog, payload, field):
    with pytest.raises(ValidationError) as error:
        change_price(catalog["offering"], owner, **payload)
    assert field in error.value.detail


@pytest.mark.django_db
def test_price_and_availability_reject_backdated_current_ranges(owner, catalog):
    price = PriceRecord.objects.get(offering=catalog["offering"], effective_to__isnull=True)
    availability = AvailabilityRecord.objects.get(offering=catalog["offering"], effective_to__isnull=True)
    before = min(price.effective_from, availability.effective_from) - timedelta(minutes=1)

    with pytest.raises(ValidationError, match="fecha"):
        change_price(catalog["offering"], owner, price_type="FIXED", amount_min=1_300_000, effective_from=before)
    with pytest.raises(ValidationError, match="fecha"):
        change_availability(catalog["offering"], owner, status="SOLD", effective_from=before)
    assert PriceRecord.objects.filter(offering=catalog["offering"], effective_to__isnull=True).count() == 1
    assert AvailabilityRecord.objects.filter(offering=catalog["offering"], effective_to__isnull=True).count() == 1


@pytest.mark.django_db
def test_listing_domain_services_enforce_permission_and_controlled_availability(catalog):
    ordinary = User.objects.create_user(
        email="ordinary@example.test", password="A-secure-test-password!", first_name="Ordinary"
    )
    with pytest.raises(PermissionDenied):
        change_price(catalog["offering"], ordinary, price_type="FIXED", amount_min=10)
    with pytest.raises(PermissionDenied):
        change_availability(catalog["offering"], ordinary, status="AVAILABLE")
    with pytest.raises(PermissionDenied) as error:
        change_availability(catalog["offering"], ordinary, status="WHATEVER")
    # El permiso se valida antes del enum para que el servicio también defienda el dominio.
    assert error.value.status_code == 403


@pytest.mark.django_db
def test_publish_validation_reports_missing_business_requirements(owner, property_type):
    offering = PropertyOffering.objects.create(
        source_type="PRIVATE", condition="USED", property_type=property_type
    )
    listing = Listing.objects.create(offering=offering, title="", slug="incompleta")
    with pytest.raises(ValidationError) as error:
        validate_publishable(listing)
    assert set(error.value.detail) == {"title", "location", "price"}

    offering.archived_at = timezone.now()
    offering.save(update_fields=["archived_at", "updated_at"])
    with pytest.raises(ValidationError) as archived_error:
        publish_listing(listing, owner)
    assert "archived" in archived_error.value.detail


@pytest.mark.django_db
def test_change_slug_is_idempotent_and_preserves_old_public_path(owner, catalog):
    listing = catalog["listing"]
    version = listing.version
    assert change_slug(listing, listing.slug, owner).version == version
    renamed = change_slug(listing, "casa-modelo-renombrada", owner)
    assert renamed.slug == "casa-modelo-renombrada"
    assert SlugRedirect.objects.filter(
        old_path="/propiedades/casa-modelo", new_path="/propiedades/casa-modelo-renombrada"
    ).exists()
