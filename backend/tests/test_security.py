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


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/v1/admin/property-types/", {"code": "csrf", "name": "CSRF"}),
        ("patch", "/api/v1/admin/listings/{listing}/", {"title": "Sin CSRF", "version": 1}),
        ("delete", "/api/v1/admin/properties/{listing}/", None),
    ],
)
def test_all_admin_write_verbs_require_csrf(owner, catalog, method, path, payload):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(owner)
    session = client.session
    session["mfa_verified"] = True
    session["mfa_verified_at"] = timezone.now().isoformat()
    session["authz_version"] = owner.authz_version
    session.save()
    path = path.format(listing=catalog["listing"].id)
    response = getattr(client, method)(path, payload or {}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_deactivated_user_cannot_continue_with_existing_session(owner, catalog):
    client = APIClient()
    client.force_login(owner)
    session = client.session
    session["mfa_verified"] = True
    session["mfa_verified_at"] = timezone.now().isoformat()
    session["authz_version"] = owner.authz_version
    session.save()
    owner.is_active = False
    owner.authz_version += 1
    owner.save(update_fields=["is_active", "authz_version", "updated_at"])
    assert client.get("/api/v1/admin/listings/").status_code in (401, 403)


@pytest.mark.django_db
def test_proxy_normalized_login_without_trailing_slash_preserves_post(client, owner):
    owner.set_password("a-secure-password")
    owner.save()
    response = client.post(
        "/api/v1/auth/login",
        {"email": owner.email, "password": "a-secure-password"},
        content_type="application/json",
    )
    assert response.status_code == 200
