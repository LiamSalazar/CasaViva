from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalog.models import PropertyOffering
from apps.crm.models import Lead, Sale
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
        {"bedrooms_max": -1},
        {"bedrooms_min": 3, "bedrooms_max": 2},
        {"bathrooms_total": -1},
        {"parking_min": -1},
        {"parking_max": -1},
        {"parking_min": 2, "parking_max": 1},
        {"levels_min": -1},
        {"levels_max": -1},
        {"levels_min": 3, "levels_max": 2},
        {"construction_area_min": -1},
        {"construction_area_max": -1},
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


@pytest.mark.django_db
def test_price_currency_and_sale_status_are_database_controlled(catalog, owner):
    now = timezone.now()
    current = PriceRecord.objects.get(offering=catalog["offering"], effective_to__isnull=True)
    current.effective_to = now
    current.save()
    with pytest.raises(IntegrityError), transaction.atomic():
        PriceRecord.objects.create(
            offering=catalog["offering"], price_type="FROM", amount_min=1,
            currency="DOG", effective_from=now,
        )
    lead = Lead.objects.create(first_name="Integridad")
    with pytest.raises(IntegrityError), transaction.atomic():
        Sale.objects.create(
            lead=lead, offering=catalog["offering"], listing=catalog["listing"],
            sale_price=1, closed_at=now, status="WHATEVER", created_by=owner,
        )
