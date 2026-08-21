import pytest
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import RecoveryCode, User
from apps.accounts.security import has_recent_mfa


@pytest.mark.django_db
def test_existing_mfa_cannot_be_reenrolled_with_password_only(client, owner):
    TOTPDevice.objects.create(user=owner, name="Principal", confirmed=True)
    login = client.post("/api/v1/auth/login/", {"email": owner.email, "password": "A-secure-test-password!"}, format="json")
    assert login.status_code == 200
    assert login.data["mfa_required"] is True
    response = client.post("/api/v1/auth/mfa/enroll/", {}, format="json")
    assert response.status_code == 403
    assert TOTPDevice.objects.filter(user=owner).count() == 1


@pytest.mark.django_db
def test_recovery_code_is_strong_hashed_single_use(client, owner):
    TOTPDevice.objects.create(user=owner, name="Principal", confirmed=True)
    raw = RecoveryCode.issue_for(owner, count=1)[0]
    stored = RecoveryCode.objects.get(user=owner)
    assert len(raw) == 32
    assert stored.code_hash != raw
    assert stored.matches(raw)

    session = client.session
    session["preauth_user_id"] = str(owner.pk)
    session.save()
    accepted = client.post("/api/v1/auth/mfa/verify/", {"code": raw}, format="json")
    assert accepted.status_code == 200
    stored.refresh_from_db()
    assert stored.used_at is not None

    session = client.session
    session["preauth_user_id"] = str(owner.pk)
    session.save()
    reused = client.post("/api/v1/auth/mfa/verify/", {"code": raw}, format="json")
    assert reused.status_code == 400


@pytest.mark.django_db
def test_mfa_reset_invalidates_previous_recovery_codes(admin_client, owner):
    TOTPDevice.objects.create(user=owner, name="Principal", confirmed=True)
    raw = RecoveryCode.issue_for(owner, count=1)[0]
    response = admin_client.post(f"/api/v1/admin/users/{owner.pk}/reset-mfa/", {}, format="json")
    assert response.status_code == 204
    assert not RecoveryCode.objects.filter(user=owner).exists()
    assert not TOTPDevice.objects.filter(user=owner).exists()
    assert not any(code.matches(raw) for code in RecoveryCode.objects.filter(user=owner))


@pytest.mark.parametrize("value", [None, "", "not-a-date", "2026-13-80"])
def test_recent_mfa_rejects_missing_or_malformed_values(rf, value):
    request = rf.get("/")
    request.session = {"mfa_verified": True}
    if value is not None:
        request.session["mfa_verified_at"] = value
    assert has_recent_mfa(request) is False


def test_recent_mfa_rejects_expired_value(rf):
    request = rf.get("/")
    request.session = {
        "mfa_verified": True,
        "mfa_verified_at": (timezone.now() - timezone.timedelta(minutes=16)).isoformat(),
    }
    assert has_recent_mfa(request) is False
