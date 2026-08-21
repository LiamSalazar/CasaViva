import base64
import io
import qrcode
from django.contrib.auth import login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import viewsets
from rest_framework.decorators import action
from django.contrib.auth.models import Group, Permission
from drf_spectacular.utils import extend_schema, OpenApiTypes
from apps.audit.services import audit_event
from .models import RecoveryCode
from .serializers import LoginSerializer, TotpSerializer, UserSerializer
from .permissions import IsMfaVerifiedAdmin
from .services import change_user_access, revoke_user_sessions
from .security import has_recent_mfa


class LoginThrottle(ScopedRateThrottle):
    scope = "login"


@ensure_csrf_cookie
@extend_schema(request=LoginSerializer, responses={200: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def password_login(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        audit_event(None, "LOGIN_FAILURE", entity_type="User", request=request, success=False)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.validated_data["user"]
    request.session["preauth_user_id"] = str(user.pk)
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    return Response({"mfa_required": bool(device), "enrollment_required": not bool(device)})


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def enroll_mfa(request):
    from .models import User
    user_id = request.session.get("preauth_user_id")
    if not user_id:
        return Response({"detail": "La autenticación previa expiró."}, status=401)
    user = User.objects.get(pk=user_id)
    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return Response({"detail": "La cuenta ya tiene MFA configurado. Verifica el dispositivo existente."}, status=403)
    device, _ = TOTPDevice.objects.get_or_create(user=user, confirmed=False, defaults={"name": "CasaViva"})
    image = qrcode.make(device.config_url)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return Response({"secret": device.key, "qr_png": base64.b64encode(output.getvalue()).decode()})


@extend_schema(request=TotpSerializer, responses={200: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def verify_mfa(request):
    from .models import User
    serializer = TotpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user_id = request.session.get("preauth_user_id")
    if not user_id:
        return Response({"detail": "La autenticación previa expiró."}, status=401)
    user = User.objects.get(pk=user_id)
    code = serializer.validated_data["code"].replace("-", "").upper()
    confirmed_device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    device = confirmed_device or TOTPDevice.objects.filter(user=user, confirmed=False).first()
    verified = bool(device and device.verify_token(code))
    recovery = None
    if not verified:
        recovery = next((candidate for candidate in RecoveryCode.objects.filter(user=user, used_at__isnull=True) if candidate.matches(code)), None)
        verified = bool(recovery)
    if not verified:
        audit_event(user, "LOGIN_FAILURE", user, request=request, success=False, reason="MFA inválido")
        return Response({"detail": "Código incorrecto."}, status=400)
    if recovery:
        from django.utils import timezone
        recovery.used_at = timezone.now()
        recovery.save(update_fields=["used_at"])
    new_codes = None
    if device and not confirmed_device and not device.confirmed:
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        new_codes = RecoveryCode.issue_for(user)
        audit_event(user, "MFA_ENABLED", user, request=request)
    login(request, user)
    request.session.pop("preauth_user_id", None)
    request.session["mfa_verified"] = True
    request.session["mfa_verified_at"] = __import__("django.utils.timezone", fromlist=["now"]).now().isoformat()
    request.session["authz_version"] = user.authz_version
    audit_event(user, "LOGIN_SUCCESS", user, request=request)
    return Response({"user": UserSerializer(user).data, "recovery_codes": new_codes})


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    audit_event(request.user, "SESSION_REVOKED", request.user, request=request)
    logout(request)
    return Response(status=204)


@extend_schema(responses={200: UserSerializer})
@api_view(["GET"])
@permission_classes([AllowAny])
def me(request):
    if not request.user.is_authenticated:
        return Response({"authenticated": False, "can_manage_users": False})
    return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = __import__("apps.accounts.models", fromlist=["User"]).User.objects.prefetch_related("groups").order_by("email", "id")
    permission_classes = [IsMfaVerifiedAdmin]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_superuser or not request.user.has_perm("accounts.manage_users"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Sólo el Owner puede administrar usuarios.")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            from rest_framework.exceptions import PermissionDenied
            if not has_recent_mfa(request):
                raise PermissionDenied("Vuelve a verificar tu identidad para cambiar accesos.")

    def perform_create(self, serializer):
        user = serializer.save()
        audit_event(self.request.user, "USER_CREATED", user, request=self.request)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        role_name = request.data.get("role_name")
        if role_name == "Owner":
            return Response({"detail": "Liam es el único superusuario ordinario."}, status=400)
        group = Group.objects.filter(name=role_name).first() if role_name else None
        change_user_access(request.user, user, group=group, is_active=request.data.get("is_active"), request=request)
        for field in ("first_name", "last_name", "email"):
            if field in request.data: setattr(user, field, request.data[field])
        if request.data.get("password"):
            user.set_password(request.data["password"]); user.last_password_change_at = __import__("django.utils.timezone", fromlist=["now"]).now(); revoke_user_sessions(user)
        user.save()
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"])
    def permissions(self, request, pk=None):
        user = self.get_object()
        codenames = request.data.get("permissions", [])
        permissions = list(Permission.objects.filter(codename__in=codenames))
        if len(permissions) != len(set(codenames)):
            return Response({"detail": "Uno o más permisos no existen."}, status=400)
        change_user_access(request.user, user, permissions=permissions, request=request)
        audit_event(request.user, "PERMISSION_GRANTED", user, request=request)
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"], url_path="revoke-sessions")
    def revoke_sessions(self, request, pk=None):
        user = self.get_object(); user.authz_version += 1; user.save(update_fields=["authz_version", "updated_at"]); revoke_user_sessions(user); audit_event(request.user, "SESSION_REVOKED", user, request=request); return Response(status=204)

    @action(detail=True, methods=["post"], url_path="reset-mfa")
    def reset_mfa(self, request, pk=None):
        user = self.get_object()
        TOTPDevice.objects.filter(user=user).delete()
        RecoveryCode.objects.filter(user=user).delete()
        user.authz_version += 1
        user.save(update_fields=["authz_version", "updated_at"])
        revoke_user_sessions(user)
        audit_event(request.user, "MFA_RESET", user, request=request)
        return Response(status=204)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Los usuarios se desactivan; no se eliminan definitivamente."}, status=405)
