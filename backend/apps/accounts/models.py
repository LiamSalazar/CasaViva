import secrets
import uuid
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Permission, PermissionsMixin
from django.db import models
from django.utils import timezone
from apps.common.models import UUIDTimeStampedModel


class RoleProfile(UUIDTimeStampedModel):
    """Business metadata layered on Django Group without replacing its auth model."""

    group = models.OneToOneField("auth.Group", on_delete=models.CASCADE, related_name="casaviva_profile")
    description = models.CharField(max_length=240, blank=True)
    is_system = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)

    class Meta:
        ordering = ["group__name"]

    def __str__(self):
        return self.group.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("El correo es obligatorio")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    authz_version = models.PositiveIntegerField(default=1)
    last_password_change_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]
    objects = UserManager()

    class Meta:
        permissions = [
            ("manage_users", "Puede administrar usuarios"),
            ("manage_roles", "Puede administrar roles"),
            ("manage_permissions", "Puede administrar permisos"),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        """Resolve explicit overrides before permissions inherited from a role."""
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        if obj is None and "." in perm:
            app_label, codename = perm.split(".", 1)
            override = self.permission_overrides.filter(
                permission__content_type__app_label=app_label,
                permission__codename=codename,
            ).values_list("effect", flat=True).first()
            if override:
                return override == PermissionOverride.Effect.ALLOW
        return super().has_perm(perm, obj)

    def get_all_permissions(self, obj=None):
        if not self.is_active:
            return set()
        permissions = set(super().get_all_permissions(obj))
        if self.is_superuser or obj is not None:
            return permissions
        for app_label, codename, effect in self.permission_overrides.values_list(
            "permission__content_type__app_label", "permission__codename", "effect"
        ):
            permission_key = f"{app_label}.{codename}"
            if effect == PermissionOverride.Effect.DENY:
                permissions.discard(permission_key)
            else:
                permissions.add(permission_key)
        return permissions


class PermissionOverride(UUIDTimeStampedModel):
    class Effect(models.TextChoices):
        ALLOW = "ALLOW", "Permitir"
        DENY = "DENY", "Denegar"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="permission_overrides")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="casaviva_overrides")
    effect = models.CharField(max_length=5, choices=Effect.choices)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="permission_overrides_created",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "permission"],
                name="unique_user_permission_override",
            )
        ]


class RecoveryCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=256)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def digest(code):
        return make_password(code)

    def matches(self, code):
        return check_password(code, self.code_hash)

    @classmethod
    def issue_for(cls, user, count=10):
        cls.objects.filter(user=user, used_at__isnull=True).delete()
        raw = [secrets.token_hex(16).upper() for _ in range(count)]
        cls.objects.bulk_create([cls(user=user, code_hash=cls.digest(code)) for code in raw])
        return raw
