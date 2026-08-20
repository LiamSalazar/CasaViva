import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User


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
