import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.catalog.models import Developer, Development, DevelopmentModel, HousingModel, PropertyOffering, PropertyType
from apps.geo.models import Municipality, State
from apps.listings.models import AvailabilityRecord, Listing, PriceRecord


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(email="owner@example.test", password="A-secure-test-password!", first_name="Owner")


@pytest.fixture
def admin_client(owner):
    client = APIClient()
    client.force_login(owner)
    session = client.session
    session["mfa_verified"] = True
    session["mfa_verified_at"] = timezone.now().isoformat()
    session["authz_version"] = owner.authz_version
    session.save()
    return client


@pytest.fixture
def property_type(db):
    return PropertyType.objects.create(code="house", name="Casa")


@pytest.fixture
def catalog(db, property_type):
    state = State.objects.create(name="Estado de México", code="MEX")
    municipality = Municipality.objects.create(state=state, name="Tecámac")
    developer = Developer.objects.create(name="Constructora", slug="constructora")
    development = Development.objects.create(developer=developer, name="Desarrollo", slug="desarrollo", state=state, municipality=municipality)
    model = HousingModel.objects.create(developer=developer, name="Modelo", slug="modelo")
    link = DevelopmentModel.objects.create(development=development, housing_model=model)
    offering = PropertyOffering.objects.create(source_type="DEVELOPER", development_model=link, property_type=property_type, bedrooms_min=3, bathrooms_total=2)
    PriceRecord.objects.create(offering=offering, price_type="FROM", amount_min=1_200_000, effective_from=timezone.now())
    AvailabilityRecord.objects.create(offering=offering, status="AVAILABLE", effective_from=timezone.now())
    listing = Listing.objects.create(offering=offering, title="Casa Modelo", slug="casa-modelo", short_description="Información clara", description="Descripción", is_published=True, published_at=timezone.now())
    return {"state": state, "municipality": municipality, "developer": developer, "development": development, "model": model, "link": link, "offering": offering, "listing": listing}
