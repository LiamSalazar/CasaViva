import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils import timezone
from apps.catalog.models import Developer, Development, DevelopmentModel, HousingModel
from apps.geo.models import Municipality, State
from apps.listings.models import AvailabilityRecord, PriceRecord
from apps.listings.services import change_availability, change_price
from apps.listings.services import hard_delete_listing
from rest_framework.exceptions import ValidationError


@pytest.mark.django_db(transaction=True)
def test_price_change_closes_previous(owner, catalog):
    record = change_price(catalog["offering"], owner, price_type="FROM", amount_min=1_350_000)
    assert record.effective_to is None
    assert PriceRecord.objects.filter(offering=catalog["offering"], effective_to__isnull=True).count() == 1
    assert PriceRecord.objects.filter(offering=catalog["offering"], effective_to__isnull=False).count() == 1


@pytest.mark.django_db(transaction=True)
def test_availability_can_return_to_available(owner, catalog):
    change_availability(catalog["offering"], owner, status="TEMPORARILY_UNAVAILABLE")
    change_availability(catalog["offering"], owner, status="AVAILABLE")
    history = list(AvailabilityRecord.objects.filter(offering=catalog["offering"]).order_by("effective_from"))
    assert [x.status for x in history] == ["AVAILABLE", "TEMPORARILY_UNAVAILABLE", "AVAILABLE"]
    assert sum(x.effective_to is None for x in history) == 1


@pytest.mark.django_db
def test_development_model_rejects_different_developer(catalog):
    other = Developer.objects.create(name="Otra", slug="otra")
    model = HousingModel.objects.create(developer=other, name="Ajeno", slug="ajeno")
    with pytest.raises(DjangoValidationError):
        DevelopmentModel.objects.create(development=catalog["development"], housing_model=model)


@pytest.mark.django_db
def test_private_offering_cannot_have_development(property_type, catalog):
    from apps.catalog.models import PropertyOffering
    with pytest.raises(IntegrityError):
        PropertyOffering.objects.create(source_type="PRIVATE", development_model=catalog["link"], property_type=property_type)


@pytest.mark.django_db
def test_hard_delete_requires_archived_record(owner, catalog):
    with pytest.raises(ValidationError, match="Primero archiva"):
        hard_delete_listing(catalog["listing"], owner, confirmation="Casa Modelo", reason="Registro duplicado")


@pytest.mark.django_db
def test_hard_delete_keeps_immutable_audit(owner, catalog):
    from apps.audit.models import AuditEvent
    from apps.listings.models import Listing

    listing = catalog["listing"]
    listing.archived_at = timezone.now()
    listing.archived_by = owner
    listing.is_published = False
    listing.save()
    listing_id = str(listing.id)

    hard_delete_listing(listing, owner, confirmation="Casa Modelo", reason="Registro creado por error")

    assert not Listing.all_objects.filter(pk=listing_id).exists()
    event = AuditEvent.objects.get(action="HARD_DELETE", entity_id=listing_id)
    assert event.old_values["title"] == "Casa Modelo"
    assert event.reason == "Registro creado por error"


@pytest.mark.django_db
def test_hard_delete_is_blocked_by_sale(owner, catalog):
    from apps.crm.models import Lead, Sale

    listing = catalog["listing"]
    listing.archived_at = timezone.now()
    listing.archived_by = owner
    listing.is_published = False
    listing.save()
    lead = Lead.objects.create(first_name="Cliente")
    Sale.objects.create(lead=lead, offering=catalog["offering"], listing=listing, sale_price=1_200_000, closed_at=timezone.now(), created_by=owner)

    with pytest.raises(ValidationError, match="historial de una venta"):
        hard_delete_listing(listing, owner, confirmation="Casa Modelo", reason="Prueba")
