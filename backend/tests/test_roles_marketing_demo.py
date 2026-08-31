from decimal import Decimal
from datetime import timedelta

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone
from django.conf import settings
from django.db import connection

from apps.accounts.models import PermissionOverride, RoleProfile, User
from apps.analytics.models import AnonymousVisitor, WebSession
from apps.crm.models import Inquiry, Lead, Sale, Visit
from apps.marketing.models import MarketingCampaign, MarketingSpend
from apps.listings.models import Listing
from apps.catalog.models import PropertyOffering
from apps.media_library.models import MediaAsset


@pytest.mark.django_db
def test_owner_creates_role_assigns_all_and_clear_and_protects_system_roles(admin_client):
    call_command("seed_system")
    options = admin_client.get("/api/v1/admin/users/permission-options/").data
    keys = [item["key"] for item in options if item["module"] == "crm"]
    created = admin_client.post("/api/v1/admin/roles/", {"name": "Coordinación comercial", "description": "Equipo de cierre", "permissions": keys}, format="json")
    assert created.status_code == 201, created.data
    assert set(created.data["permission_keys"]) == set(keys)
    cleared = admin_client.patch(f"/api/v1/admin/roles/{created.data['id']}/", {"permissions": []}, format="json")
    assert cleared.status_code == 200
    assert cleared.data["permission_keys"] == []
    owner_role = next(role for role in admin_client.get("/api/v1/admin/roles/").data["results"] if role["is_owner"])
    assert admin_client.delete(f"/api/v1/admin/roles/{owner_role['id']}/").status_code == 409


@pytest.mark.django_db
def test_permission_options_only_expose_casaviva_functional_permissions(admin_client):
    call_command("seed_system")
    options = admin_client.get("/api/v1/admin/users/permission-options/").data
    keys = {item["key"] for item in options}
    from apps.accounts.services import BUSINESS_PERMISSIONS
    assert {"crm.manage_sales", "catalog.manage_offerings", "analytics.view_bi"} <= keys
    assert keys == set(BUSINESS_PERMISSIONS)
    assert not any(item.rsplit(".", 1)[-1].startswith(prefix) for item in keys for prefix in ("add_", "change_", "delete_"))


@pytest.mark.django_db
def test_role_assignment_deny_precedence_and_reset_to_role(admin_client):
    call_command("seed_system")
    user = User.objects.create_user(email="commercial@example.test", password="A-secure-test-password!", first_name="Comercial")
    user.groups.add(Group.objects.get(name="Comercial"))
    permission = Permission.objects.get(content_type__app_label="crm", codename="manage_sales")
    PermissionOverride.objects.create(user=user, permission=permission, effect="DENY")
    assert not user.has_perm("crm.manage_sales")
    response = admin_client.post(f"/api/v1/admin/users/{user.id}/reset-to-role/", {}, format="json")
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.has_perm("crm.manage_sales")
    assert not user.permission_overrides.exists()


@pytest.mark.django_db
def test_seed_groups_does_not_overwrite_human_role_changes():
    call_command("seed_system")
    commercial = Group.objects.get(name="Comercial")
    permission = Permission.objects.get(content_type__app_label="crm", codename="manage_sales")
    commercial.permissions.remove(permission)
    profile = RoleProfile.objects.get(group=commercial)
    profile.description = "Descripción ajustada por Liam"
    profile.save(update_fields=["description"])
    owner, founder = __import__("apps.accounts.services", fromlist=["seed_groups"]).seed_groups()
    commercial.refresh_from_db()
    assert permission not in commercial.permissions.all()
    assert RoleProfile.objects.get(group=commercial).description == "Descripción ajustada por Liam"
    assert Group.objects.filter(name="Comercial").count() == 1


@pytest.mark.django_db
def test_campaign_budget_spend_and_automatic_commission_metrics(admin_client, owner, catalog):
    now = timezone.now()
    campaign = MarketingCampaign.objects.create(name="Instagram agosto", utm_campaign="instagram_agosto", channel="INSTAGRAM", planned_budget=10_000, utm_source="instagram", utm_medium="paid_social", default_landing_path="/propiedades", start_date=now.date(), created_by=owner, updated_by=owner)
    MarketingSpend.objects.create(campaign=campaign, date=now.date(), amount=4_800)
    lead = Lead.objects.create(first_name="Cliente")
    visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    WebSession.objects.create(visitor=visitor, lead=lead, started_at=now, last_seen_at=now, utm_source="instagram", utm_medium="paid_social", utm_campaign=campaign.utm_campaign, landing_path="/propiedades", consent_state="granted")
    Inquiry.objects.create(lead=lead, listing=catalog["listing"], channel="WEB")
    Visit.objects.create(lead=lead, offering=catalog["offering"], scheduled_at=now, status="COMPLETED", completed_at=now)
    Sale.objects.create(lead=lead, offering=catalog["offering"], listing=catalog["listing"], sale_price=1_500_000, commission_amount=45_000, closed_at=now, created_by=owner)
    response = admin_client.get(f"/api/v1/admin/marketing-campaigns/{campaign.id}/results/")
    assert response.status_code == 200
    assert response.data["available_budget"] == Decimal("5200.00")
    assert response.data["execution_percent"] == 48.0
    assert response.data["cost_per_sale"] == Decimal("4800.00")
    assert response.data["contribution_after_advertising"] == Decimal("40200.00")
    assert response.data["return_on_ad_spend"] == Decimal("9.375")
    assert "profit" not in response.data and "ganancia" not in response.data


@pytest.mark.django_db
def test_campaign_results_use_bi_first_touch_once(admin_client, owner, catalog):
    now = timezone.now()
    campaign_a = MarketingCampaign.objects.create(name="Campaña A", utm_campaign="campana_a", channel="INSTAGRAM", utm_source="instagram", utm_medium="paid_social", start_date=now.date(), created_by=owner, updated_by=owner)
    campaign_b = MarketingCampaign.objects.create(name="Campaña B", utm_campaign="campana_b", channel="FACEBOOK", utm_source="facebook", utm_medium="paid_social", start_date=now.date(), created_by=owner, updated_by=owner)
    lead = Lead.objects.create(first_name="First touch")
    visitor = AnonymousVisitor.objects.create(first_seen_at=now - timedelta(days=2), last_seen_at=now)
    WebSession.objects.create(visitor=visitor, lead=lead, started_at=now - timedelta(days=2), last_seen_at=now - timedelta(days=2), utm_campaign=campaign_a.utm_campaign, consent_state="granted")
    WebSession.objects.create(visitor=visitor, lead=lead, started_at=now - timedelta(days=1), last_seen_at=now - timedelta(days=1), utm_campaign=campaign_b.utm_campaign, consent_state="granted")
    Sale.objects.create(lead=lead, offering=catalog["offering"], listing=catalog["listing"], sale_price=900_000, commission_amount=27_000, closed_at=now, created_by=owner)
    result_a = admin_client.get(f"/api/v1/admin/marketing-campaigns/{campaign_a.id}/results/").data
    result_b = admin_client.get(f"/api/v1/admin/marketing-campaigns/{campaign_b.id}/results/").data
    assert result_a["acquired_clients"] == 1
    assert result_a["closed_sales"] == 1
    assert result_b["acquired_clients"] == 0
    assert result_b["closed_sales"] == 0


@pytest.mark.django_db
def test_demo_commands_abort_against_normal_database(monkeypatch):
    monkeypatch.setenv("CASAVIVA_MODE", "demo")
    with override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "casaviva"}}):
        with pytest.raises(CommandError, match="ABORTADO"):
            call_command("reset_demo_data")
        with pytest.raises(CommandError, match="ABORTADO"):
            call_command("seed_demo")


@pytest.mark.skipif(connection.vendor != "sqlite", reason="El seed integral se cubre una vez en la suite SQLite; el aislamiento PostgreSQL se valida por Compose.")
@pytest.mark.django_db(transaction=True)
def test_seed_demo_is_idempotent_and_populates_business_areas(monkeypatch):
    monkeypatch.setenv("CASAVIVA_MODE", "demo")
    monkeypatch.setenv("DEMO_OWNER_PASSWORD", "Demo-only-secure-password!")
    monkeypatch.setenv("DEMO_TOTP_SECRET", "3132333435363738393031323334353637383930")
    monkeypatch.setitem(settings.DATABASES["default"], "NAME", "casaviva_demo")
    call_command("seed_system")
    call_command("seed_reference_catalog")
    call_command("seed_demo")
    counts = (MarketingCampaign.objects.count(), Lead.objects.count(), Inquiry.objects.count(), Visit.objects.count(), Sale.objects.count())
    call_command("seed_demo")
    assert counts == (10, 72, 88, 36, 14)
    assert (MarketingCampaign.objects.count(), Lead.objects.count(), Inquiry.objects.count(), Visit.objects.count(), Sale.objects.count()) == counts
    assert Listing.all_objects.count() >= 60
    assert WebSession.objects.count() >= 200
    photos = MediaAsset.objects.filter(alt_text__startswith="demo-real-photo-")
    assert photos.count() >= 10
    assert all(photo.mime_type.startswith("image/") for photo in photos)
    call_command("reset_demo_data")
    assert PropertyOffering.objects.count() >= 60
