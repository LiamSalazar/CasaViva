import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from django.contrib.auth.models import Group


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
    first = admin_client.patch(f"/api/v1/admin/listings/{listing.id}/", {"title": "Cambio Ana", "version": 1}, format="json")
    assert first.status_code == 200
    stale = admin_client.patch(f"/api/v1/admin/listings/{listing.id}/", {"title": "Cambio Alfredo", "version": 1}, format="json")
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
    assert client.post(f"/api/v1/admin/listings/{catalog['listing'].id}/unpublish/", {}, format="json").status_code == 200
    assert client.post(f"/api/v1/admin/listings/{catalog['listing'].id}/publish/", {}, format="json").status_code == 200

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
