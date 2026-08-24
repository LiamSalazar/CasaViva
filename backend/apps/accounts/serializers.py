from django.contrib.auth import authenticate
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers
from .models import User
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name", read_only=True)
    role = serializers.SerializerMethodField()
    mfa_enabled = serializers.SerializerMethodField()
    can_manage_users = serializers.SerializerMethodField()
    effective_permissions = serializers.SerializerMethodField()
    direct_permissions = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=12)
    role_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "name", "role", "role_name", "password", "is_active", "last_login", "mfa_enabled", "can_manage_users", "authz_version", "effective_permissions", "direct_permissions"]
        read_only_fields = ["id", "last_login", "authz_version"]

    def get_role(self, obj):
        return "Owner" if obj.is_superuser else (obj.groups.first().name if obj.groups.exists() else "Sin rol")

    def get_mfa_enabled(self, obj):
        return TOTPDevice.objects.filter(user=obj, confirmed=True).exists()

    def get_can_manage_users(self, obj):
        return obj.is_superuser and obj.has_perm("accounts.manage_users")

    def get_effective_permissions(self, obj):
        return sorted(obj.get_all_permissions())

    def get_direct_permissions(self, obj):
        return sorted(f"{permission.content_type.app_label}.{permission.codename}" for permission in obj.user_permissions.select_related("content_type"))

    def create(self, validated_data):
        role = validated_data.pop("role_name", "Founder Admin")
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "La contraseña inicial es obligatoria."})
        if role == "Owner":
            raise serializers.ValidationError({"role_name": "No se pueden crear otros superusuarios desde esta interfaz."})
        group = Group.objects.filter(name=role).first()
        if not group:
            raise serializers.ValidationError({"role_name": "El rol no existe."})
        validate_password(password)
        user = User.objects.create_user(password=password, is_staff=False, is_superuser=False, **validated_data)
        user.groups.add(group)
        return user


class AdminUserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    role_name = serializers.CharField(max_length=150, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        unexpected = set(self.initial_data) - set(self.fields)
        if unexpected:
            raise serializers.ValidationError({key: "Este campo no puede modificarse." for key in unexpected})
        user = self.context["user"]
        email = attrs.get("email")
        if email:
            email = email.lower().strip()
            if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({"email": "Ya existe un usuario con este correo."})
            attrs["email"] = email
        password = attrs.get("password")
        if password:
            validate_password(password, user=user)
        role_name = attrs.get("role_name")
        if role_name == "Owner":
            raise serializers.ValidationError({"role_name": "No se pueden asignar otros usuarios Owner desde esta interfaz."})
        if role_name and not Group.objects.filter(name=role_name).exists():
            raise serializers.ValidationError({"role_name": "El rol no existe."})
        return attrs


class UserPermissionsSerializer(serializers.Serializer):
    permissions = serializers.ListField(child=serializers.CharField(max_length=160), allow_empty=True, max_length=200)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        user = authenticate(self.context["request"], username=attrs["email"].lower(), password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError("Correo o contraseña incorrectos.")
        attrs["user"] = user
        return attrs


class TotpSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=64)
