from django.contrib.auth import authenticate
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers
from .models import User
from django.contrib.auth.models import Group


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name", read_only=True)
    role = serializers.SerializerMethodField()
    mfa_enabled = serializers.SerializerMethodField()
    can_manage_users = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=12)
    role_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "name", "role", "role_name", "password", "is_active", "last_login", "mfa_enabled", "can_manage_users", "authz_version"]
        read_only_fields = ["id", "last_login", "authz_version"]

    def get_role(self, obj):
        return "Owner" if obj.is_superuser else (obj.groups.first().name if obj.groups.exists() else "Sin rol")

    def get_mfa_enabled(self, obj):
        return TOTPDevice.objects.filter(user=obj, confirmed=True).exists()

    def get_can_manage_users(self, obj):
        return obj.is_superuser and obj.has_perm("accounts.manage_users")

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
        user = User.objects.create_user(password=password, is_staff=False, is_superuser=False, **validated_data)
        user.groups.add(group)
        return user


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
