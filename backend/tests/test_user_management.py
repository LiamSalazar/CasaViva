from io import StringIO

import pytest
from django.core.management import call_command
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import RecoveryCode, User
from apps.audit.models import AuditEvent


@pytest.mark.django_db
def test_first_mfa_enrollment_requires_preauth_and_confirms_new_device(client, owner):
    assert client.post("/api/v1/auth/mfa/enroll/", {}, format="json").status_code == 401
    assert client.post("/api/v1/auth/mfa/verify/", {"code": "000000"}, format="json").status_code == 401

    login = client.post(
        "/api/v1/auth/login/",
        {"email": owner.email.upper(), "password": "A-secure-test-password!"},
        format="json",
    )
    assert login.status_code == 200
    assert login.data == {"mfa_required": False, "enrollment_required": True}
    enrolled = client.post("/api/v1/auth/mfa/enroll/", {}, format="json")
    assert enrolled.status_code == 200
    device = TOTPDevice.objects.get(user=owner, confirmed=False)
    token = str(totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits)).zfill(device.digits)
    verified = client.post("/api/v1/auth/mfa/verify/", {"code": token}, format="json")
    assert verified.status_code == 200
    assert len(verified.data["recovery_codes"]) == 10
    assert TOTPDevice.objects.filter(user=owner, confirmed=True).exists()
    assert RecoveryCode.objects.filter(user=owner).count() == 10


@pytest.mark.django_db
def test_owner_user_crud_rejects_escalation_and_revokes_security_state(admin_client):
    call_command("seed_system")
    base = {
        "email": "future@example.test",
        "first_name": "Future",
        "last_name": "Admin",
        "password": "A-secure-test-password!",
        "role_name": "Founder Admin",
        "is_active": True,
    }
    created = admin_client.post("/api/v1/admin/users/", base, format="json")
    assert created.status_code == 201, created.data
    target = User.objects.get(pk=created.data["id"])
    assert target.groups.get().name == "Founder Admin"

    invalid_permission = admin_client.post(
        f"/api/v1/admin/users/{target.id}/permissions/",
        {"permissions": ["permission_that_does_not_exist"]},
        format="json",
    )
    assert invalid_permission.status_code == 400
    assert admin_client.patch(
        f"/api/v1/admin/users/{target.id}/", {"role_name": "Owner"}, format="json"
    ).status_code == 400

    TOTPDevice.objects.create(user=target, name="Principal", confirmed=True)
    RecoveryCode.issue_for(target, count=1)
    previous_version = target.authz_version
    assert admin_client.post(f"/api/v1/admin/users/{target.id}/revoke-sessions/", {}, format="json").status_code == 204
    target.refresh_from_db()
    assert target.authz_version == previous_version + 1
    assert admin_client.post(f"/api/v1/admin/users/{target.id}/reset-mfa/", {}, format="json").status_code == 204
    assert not TOTPDevice.objects.filter(user=target).exists()
    assert not RecoveryCode.objects.filter(user=target).exists()
    assert admin_client.delete(f"/api/v1/admin/users/{target.id}/").status_code == 405


@pytest.mark.django_db
def test_admin_listing_and_interactive_password_reset_never_expose_secrets(owner, monkeypatch):
    output = StringIO()
    call_command("list_admin_users", stdout=output)
    text = output.getvalue()
    assert owner.email in text and "Owner" in text
    assert owner.password not in text

    previous_version = owner.authz_version
    answers = iter(["Another-secure-test-password!", "Another-secure-test-password!"])
    monkeypatch.setattr("apps.accounts.management.commands.reset_admin_password.getpass.getpass", lambda prompt: next(answers))
    reset_output = StringIO()
    call_command("reset_admin_password", owner.email.upper(), stdout=reset_output)
    owner.refresh_from_db()
    assert owner.check_password("Another-secure-test-password!")
    assert owner.authz_version == previous_version + 1
    assert "Another-secure-test-password!" not in reset_output.getvalue()
    assert AuditEvent.objects.filter(entity_id=str(owner.id), action="PASSWORD_CHANGED").exists()
