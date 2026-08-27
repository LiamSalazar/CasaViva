from django.contrib.auth.models import Group, Permission
from django.contrib.sessions.models import Session
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.audit.services import audit_event
from .models import PermissionOverride, RoleProfile


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

DEFAULT_ROLES = {
    "Founder Admin": {
        "description": "Acceso general a la operación de CasaViva.",
        "permissions": BUSINESS_PERMISSIONS,
    },
    "Operaciones e inventario": {
        "description": "Propiedades, desarrolladoras, desarrollos, modelos y catálogos.",
        "permissions": [key for key in BUSINESS_PERMISSIONS if key.startswith("catalog.") or key.startswith("listings.")],
    },
    "Comercial": {
        "description": "Clientes, consultas, visitas y ventas.",
        "permissions": [key for key in BUSINESS_PERMISSIONS if key.startswith("crm.")],
    },
    "Marketing y BI": {
        "description": "Campañas, gasto publicitario y resultados.",
        "permissions": [key for key in BUSINESS_PERMISSIONS if key.startswith("marketing.") or key == "analytics.view_bi"],
    },
    "Contenido": {
        "description": "Contenido editorial, guías y ubicaciones públicas.",
        "permissions": ["content.manage_content"],
    },
}


@transaction.atomic
def seed_groups():
    owner, owner_created = Group.objects.get_or_create(name="Owner")
    by_key = {f"{p.content_type.app_label}.{p.codename}": p for p in Permission.objects.select_related("content_type")}
    if owner_created:
        owner.permissions.set([by_key[key] for key in BUSINESS_PERMISSIONS + SECURITY_PERMISSIONS if key in by_key])
    RoleProfile.objects.get_or_create(group=owner, defaults={"description": "Propietario reservado de CasaViva.", "is_system": True, "is_owner": True})
    roles = {}
    for name, config in DEFAULT_ROLES.items():
        group, created = Group.objects.get_or_create(name=name)
        if created:
            group.permissions.set([by_key[key] for key in config["permissions"] if key in by_key])
        RoleProfile.objects.get_or_create(group=group, defaults={"description": config["description"], "is_system": True, "is_owner": False})
        roles[name] = group
    return owner, roles["Founder Admin"]


def reset_permission_overrides(actor, user, request=None):
    if not actor.is_superuser or not actor.has_perm("accounts.manage_permissions"):
        raise PermissionDenied("Sólo el Owner puede modificar accesos.")
    if user.is_superuser:
        raise ValidationError("Los permisos del Owner no pueden limitarse.")
    PermissionOverride.objects.filter(user=user).delete()
    user.authz_version += 1
    user.save(update_fields=["authz_version", "updated_at"])
    revoke_user_sessions(user)
    audit_event(actor, "PERMISSION_RESET", user, request=request)
    return user


def revoke_user_sessions(user, except_session=None):
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if data.get("_auth_user_id") == str(user.pk) and session.session_key != except_session:
            session.delete()


def managed_permissions_queryset():
    functional_filter = Q()
    for key in BUSINESS_PERMISSIONS:
        app_label, codename = key.split(".", 1)
        functional_filter |= Q(content_type__app_label=app_label, codename=codename)
    return Permission.objects.select_related("content_type").filter(functional_filter)


@transaction.atomic
def set_effective_permissions(actor, user, desired_permissions, request=None):
    """Persist only the differences between a role and the desired effective access."""
    if not actor.is_superuser or not actor.has_perm("accounts.manage_permissions"):
        raise PermissionDenied("Sólo el Owner puede modificar accesos.")
    if user.is_superuser:
        raise ValidationError("Los permisos del Owner no pueden limitarse mediante overrides.")
    desired_ids = {permission.pk for permission in desired_permissions}
    inherited_ids = set(
        Permission.objects.filter(group__user=user).values_list("pk", flat=True)
    )
    managed = list(managed_permissions_queryset())
    managed_ids = {permission.pk for permission in managed}
    user.user_permissions.remove(*user.user_permissions.filter(pk__in=managed_ids))
    for permission in managed:
        desired = permission.pk in desired_ids
        inherited = permission.pk in inherited_ids
        if desired == inherited:
            PermissionOverride.objects.filter(user=user, permission=permission).delete()
        else:
            PermissionOverride.objects.update_or_create(
                user=user,
                permission=permission,
                defaults={
                    "effect": PermissionOverride.Effect.ALLOW if desired else PermissionOverride.Effect.DENY,
                    "created_by": actor,
                },
            )
    user.authz_version += 1
    user.save(update_fields=["authz_version", "updated_at"])
    revoke_user_sessions(user)
    audit_event(
        actor, "PERMISSION_GRANTED", user,
        new_values={"effective_permissions": sorted(f"{p.content_type.app_label}.{p.codename}" for p in desired_permissions)},
        request=request,
    )
    return user


@transaction.atomic
def change_user_access(actor, user, *, group=None, is_active=None, permissions=None, request=None):
    if not actor.is_superuser or not actor.has_perm("accounts.manage_permissions"):
        raise PermissionDenied("Sólo el Owner puede modificar accesos.")
    if actor.pk == user.pk and (group is not None or is_active is False):
        raise ValidationError("No puedes retirar tu propio acceso Owner.")
    before = {"is_active": user.is_active, "groups": list(user.groups.values_list("name", flat=True))}
    if is_active is not None:
        user.is_active = is_active
    if group is not None:
        user.groups.set([group])
    if permissions is not None:
        set_effective_permissions(actor, user, permissions, request=request)
        user.refresh_from_db()
    else:
        user.authz_version += 1
        user.save(update_fields=["is_active", "authz_version", "updated_at"])
        revoke_user_sessions(user)
    if group is not None or is_active is not None:
        audit_event(actor, "ROLE_CHANGED", user, old_values=before, new_values={"is_active": user.is_active, "groups": list(user.groups.values_list("name", flat=True))}, request=request)
    return user
