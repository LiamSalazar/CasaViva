import pytest
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_admin_requires_mfa(owner, catalog):
    client = APIClient(); client.force_login(owner)
    session = client.session; session["authz_version"] = owner.authz_version; session.save()
    assert client.get("/api/v1/admin/listings/").status_code == 403


@pytest.mark.django_db
def test_authz_version_change_revokes_existing_session(owner, catalog):
    client = APIClient(); client.force_login(owner)
    session = client.session; session["mfa_verified"] = True; session["authz_version"] = owner.authz_version; session.save()
    owner.authz_version += 1; owner.save(update_fields=["authz_version", "updated_at"])
    assert client.get("/api/v1/admin/listings/").status_code in (401, 403)


@pytest.mark.django_db
def test_session_authenticated_write_requires_csrf(owner, catalog):
    client = APIClient(enforce_csrf_checks=True); client.force_login(owner)
    session = client.session; session["mfa_verified"] = True; session["mfa_verified_at"] = timezone.now().isoformat(); session["authz_version"] = owner.authz_version; session.save()
    response = client.patch(f"/api/v1/admin/listings/{catalog['listing'].id}/", {"title": "Sin CSRF", "version": 1}, format="json")
    assert response.status_code == 403
