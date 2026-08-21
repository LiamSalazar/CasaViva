from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalog.models import PropertyOffering
from apps.listings.models import AvailabilityRecord, PriceRecord


@pytest.mark.django_db
def test_partial_unique_constraints_allow_only_one_current_record(catalog):
    offering = catalog["offering"]
    with pytest.raises(IntegrityError), transaction.atomic():
        PriceRecord.objects.create(offering=offering, price_type="FROM", amount_min=2, effective_from=timezone.now())
    with pytest.raises(IntegrityError), transaction.atomic():
        AvailabilityRecord.objects.create(offering=offering, status="SOLD", effective_from=timezone.now())


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fields",
    [
        {"bedrooms_min": -1},
        {"bathrooms_total": -1},
        {"construction_area_min": -1},
        {"land_area_min": 20, "land_area_max": 10},
        {"latitude": 91},
        {"longitude": -181},
        {"default_commission_rate": 101},
    ],
)
def test_offering_constraints_reject_invalid_numeric_values(catalog, fields):
    values = {
        "source_type": "DEVELOPER", "condition": "NEW",
        "development_model": catalog["link"], "property_type": catalog["offering"].property_type,
        **fields,
    }
    with pytest.raises(IntegrityError), transaction.atomic():
        PropertyOffering.objects.create(**values)


@pytest.mark.django_db
def test_price_and_availability_periods_cannot_end_before_they_start(catalog):
    now = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        PriceRecord.objects.create(
            offering=catalog["offering"], price_type="FROM", amount_min=1,
            effective_from=now, effective_to=now - timedelta(seconds=1),
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        AvailabilityRecord.objects.create(
            offering=catalog["offering"], status="AVAILABLE",
            effective_from=now, effective_to=now - timedelta(seconds=1),
        )
