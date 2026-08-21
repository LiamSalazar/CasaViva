from django.contrib.auth.models import Group, Permission
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.audit.services import audit_event


BUSINESS_PERMISSIONS = [
    "catalog.manage_developers", "catalog.manage_developments", "catalog.manage_models",
    "catalog.manage_offerings", "catalog.manage_catalogs", "listings.publish_listing",
    "listings.unpublish_listing", "listings.archive_listing", "listings.restore_listing",
    "listings.hard_delete_listing", "crm.manage_leads", "crm.manage_inquiries",
    "crm.manage_visits", "crm.manage_sales", "content.manage_content",
    "analytics.view_bi", "marketing.view_campaigns", "marketing.manage_campaigns",
    "marketing.view_spend", "marketing.manage_spend",
    "audit.view_audit", "audit.hard_delete_business_record",
]
SECURITY_PERMISSIONS = ["accounts.manage_users", "accounts.manage_roles", "accounts.manage_permissions"]


@transaction.atomic
def seed_groups():
    owner, _ = Group.objects.get_or_create(name="Owner")
    founder, _ = Group.objects.get_or_create(name="Founder Admin")
    by_key = {f"{p.content_type.app_label}.{p.codename}": p for p in Permission.objects.select_related("content_type")}
    founder.permissions.set([by_key[key] for key in BUSINESS_PERMISSIONS if key in by_key])
    owner.permissions.set([by_key[key] for key in BUSINESS_PERMISSIONS + SECURITY_PERMISSIONS if key in by_key])
    return owner, founder


def revoke_user_sessions(user, except_session=None):
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if data.get("_auth_user_id") == str(user.pk) and session.session_key != except_session:
            session.delete()


@transaction.atomic
def change_user_access(actor, user, *, group=None, is_active=None, permissions=None, request=None):
    if not actor.is_superuser or not actor.has_perm("accounts.manage_permissions"):
        raise PermissionDenied("Sólo el Owner puede modificar accesos.")
    if actor.pk == user.pk and (group is not None or is_active is False):
        raise ValidationError("No puedes retirar tu propio acceso Owner.")
    before = {"is_active": user.is_active, "groups": list(user.groups.values_list("name", flat=True))}
    if is_active is not None:
        user.is_active = is_active
    user.authz_version += 1
    user.save(update_fields=["is_active", "authz_version", "updated_at"])
    if group is not None:
        user.groups.set([group])
    if permissions is not None:
        user.user_permissions.set(permissions)
    revoke_user_sessions(user)
    audit_event(actor, "ROLE_CHANGED", user, old_values=before, new_values={"is_active": user.is_active, "groups": list(user.groups.values_list("name", flat=True))}, request=request)
    return user
