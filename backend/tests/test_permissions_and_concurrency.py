import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from apps.marketing.models import MarketingCampaign


def verified_client(user):
    client = APIClient(); client.force_login(user)
    session = client.session; session["mfa_verified"] = True; session["mfa_verified_at"] = timezone.now().isoformat(); session["authz_version"] = user.authz_version; session.save()
    return client


@pytest.mark.django_db
def test_founder_can_manage_business_but_not_users(catalog):
    call_command("seed_system")
    ana = User.objects.create_user(email="ana@example.test", password="A-secure-test-password!", first_name="Ana")
    ana.groups.add(__import__("django.contrib.auth.models", fromlist=["Group"]).Group.objects.get(name="Founder Admin"))
    client = verified_client(ana)
    assert client.get("/api/v1/admin/listings/").status_code == 200
    assert client.get("/api/v1/admin/users/").status_code == 403


@pytest.mark.django_db
def test_anonymous_cannot_access_admin(client):
    assert client.get("/api/v1/admin/listings/").status_code in (401, 403)


@pytest.mark.django_db
def test_optimistic_lock_returns_409(admin_client, catalog):
    listing = catalog["listing"]
    first = admin_client.post(
        f"/api/v1/admin/properties/{listing.id}/featured/",
        {"is_featured": True, "listing_version": listing.version}, format="json",
    )
    assert first.status_code == 200
    stale = admin_client.post(
        f"/api/v1/admin/properties/{listing.id}/featured/",
        {"is_featured": False, "listing_version": listing.version}, format="json",
    )
    assert stale.status_code == 409


@pytest.mark.django_db
@pytest.mark.parametrize(("first_name", "email"), [("Ana", "ana-matrix@example.test"), ("Alfredo", "alfredo-matrix@example.test")])
def test_founder_permission_matrix_for_sensitive_business_actions(catalog, first_name, email):
    call_command("seed_system")
    founder = User.objects.create_user(email=email, password="A-secure-test-password!", first_name=first_name)
    founder.groups.add(Group.objects.get(name="Founder Admin"))
    client = verified_client(founder)

    assert client.post("/api/v1/admin/property-types/", {"code": f"duplex-{first_name.lower()}", "name": "Dúplex", "is_active": True, "sort_order": 10}, format="json").status_code == 201
    assert client.get("/api/v1/admin/bi/overview/").status_code == 200
    assert client.get("/api/v1/admin/audit/").status_code == 200
    listing = catalog["listing"]
    unpublished = client.post(
        f"/api/v1/admin/properties/{listing.id}/publication/",
        {"is_published": False, "listing_version": listing.version}, format="json",
    )
    assert unpublished.status_code == 200, unpublished.data
    published = client.post(
        f"/api/v1/admin/properties/{listing.id}/publication/",
        {"is_published": True, "listing_version": unpublished.data["version"]}, format="json",
    )
    assert published.status_code == 200, published.data

    forbidden_user = User.objects.create_user(email=f"future-{email}", password="A-secure-test-password!", first_name="Future")
    assert client.post("/api/v1/admin/users/", {}, format="json").status_code == 403
    assert client.patch(f"/api/v1/admin/users/{forbidden_user.id}/", {"is_active": False}, format="json").status_code == 403
    assert client.post(f"/api/v1/admin/users/{forbidden_user.id}/permissions/", {"permissions": []}, format="json").status_code == 403
    assert client.post(f"/api/v1/admin/users/{forbidden_user.id}/reset-mfa/", {}, format="json").status_code == 403
    assert client.post(f"/api/v1/admin/users/{forbidden_user.id}/revoke-sessions/", {}, format="json").status_code == 403

    assert client.delete(f"/api/v1/admin/properties/{catalog['listing'].id}/").status_code == 204
    assert client.post(f"/api/v1/admin/properties/{catalog['listing'].id}/restore/", {}, format="json").status_code == 200
    assert client.delete(f"/api/v1/admin/properties/{catalog['listing'].id}/").status_code == 204
    assert client.post(
        f"/api/v1/admin/properties/{catalog['listing'].id}/hard-delete/",
        {"confirmation": catalog["listing"].title, "reason": "Registro de prueba creado por error"},
        format="json",
    ).status_code == 204


@pytest.mark.django_db
def test_owner_access_change_invalidates_target_session(owner):
    call_command("seed_system")
    target = User.objects.create_user(email="target@example.test", password="A-secure-test-password!", first_name="Target")
    target.groups.add(Group.objects.get(name="Founder Admin"))
    target_client = verified_client(target)
    owner_client = verified_client(owner)
    response = owner_client.patch(
        f"/api/v1/admin/users/{target.id}/",
        {"role_name": "Founder Admin", "is_active": True},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert target_client.get("/api/v1/admin/listings/").status_code in (401, 403)


@pytest.mark.django_db
def test_bi_analyst_can_read_but_cannot_mutate_marketing(owner):
    call_command("seed_system")
    analyst = User.objects.create_user(email="analyst@example.test", password="A-secure-test-password!", first_name="Analyst")
    analyst.user_permissions.add(Permission.objects.get(content_type__app_label="analytics", codename="view_bi"))
    client = verified_client(analyst)
    campaign = MarketingCampaign.objects.create(name="Lectura", utm_campaign="lectura", channel="Social", start_date=timezone.now().date())
    assert client.get("/api/v1/admin/bi/overview/").status_code == 200
    assert client.get("/api/v1/admin/marketing-campaigns/").status_code == 200
    assert client.post("/api/v1/admin/marketing-campaigns/", {"name": "No", "utm_campaign": "no", "channel": "Social", "start_date": timezone.now().date()}, format="json").status_code == 403
    assert client.patch(f"/api/v1/admin/marketing-campaigns/{campaign.id}/", {"name": "No"}, format="json").status_code == 403
    assert client.delete(f"/api/v1/admin/marketing-campaigns/{campaign.id}/").status_code == 403


@pytest.mark.django_db
def test_founder_deactivates_campaign_instead_of_deleting_history(catalog):
    call_command("seed_system")
    founder = User.objects.create_user(email="marketing@example.test", password="A-secure-test-password!", first_name="Marketing")
    founder.groups.add(Group.objects.get(name="Founder Admin"))
    client = verified_client(founder)
    campaign = MarketingCampaign.objects.create(name="Histórica", utm_campaign="historica", channel="Social", start_date=timezone.now().date())
    assert client.delete(f"/api/v1/admin/marketing-campaigns/{campaign.id}/").status_code == 204
    campaign.refresh_from_db()
    assert campaign.is_active is False and campaign.archived_at is not None


@pytest.mark.django_db
def test_legacy_listing_endpoint_cannot_bypass_property_lifecycle(admin_client, catalog):
    listing = catalog["listing"]
    assert admin_client.patch(f"/api/v1/admin/listings/{listing.id}/", {"title": "Bypass", "version": listing.version}, format="json").status_code == 405
    assert admin_client.delete(f"/api/v1/admin/listings/{listing.id}/").status_code == 405
    assert admin_client.post(f"/api/v1/admin/listings/{listing.id}/unpublish/", {}, format="json").status_code in (404, 405)
    listing.refresh_from_db()
    assert listing.title == "Casa Modelo" and listing.is_published is True
    offering = catalog["offering"]
    bypass = admin_client.patch(
        f"/api/v1/admin/offerings/{offering.id}/",
        {"internal_notes": "Bypass", "version": offering.version}, format="json",
    )
    assert bypass.status_code == 400
    offering.refresh_from_db()
    assert offering.internal_notes is None
