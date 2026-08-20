from rest_framework.permissions import BasePermission


class IsMfaVerifiedAdmin(BasePermission):
    message = "Se requiere una sesión administrativa con MFA verificado."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.session.get("mfa_verified")
        )


class DjangoModelPermission(BasePermission):
    permission = None

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and (request.user.is_superuser or request.user.has_perm(self.permission)))


class HasRequiredPermission(BasePermission):
    message = "No tienes permiso para realizar esta acción."

    def has_permission(self, request, view):
        permission = getattr(view, "required_permission", None)
        return bool(permission and (request.user.is_superuser or request.user.has_perm(permission)))


class CanViewBI(DjangoModelPermission):
    permission = "analytics.view_bi"


class CanViewAudit(DjangoModelPermission):
    permission = "audit.view_audit"
