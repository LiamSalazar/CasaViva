from django.core.management.base import BaseCommand
from django.db.models import Q
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Lista cuentas administrativas sin mostrar secretos ni credenciales."

    def handle(self, *args, **options):
        users = User.objects.filter(Q(is_staff=True) | Q(groups__name__in=["Owner", "Founder Admin"])).distinct().order_by("first_name", "email")
        if not users:
            self.stdout.write("No hay cuentas administrativas creadas en esta base de datos.")
            return
        for user in users:
            role = "Owner" if user.is_superuser else user.groups.values_list("name", flat=True).first() or "Sin rol"
            mfa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
            self.stdout.write(user.full_name or user.email)
            self.stdout.write(f"  email: {user.email}")
            self.stdout.write(f"  rol: {role}")
            self.stdout.write(f"  activo: {'sí' if user.is_active else 'no'}")
            self.stdout.write(f"  MFA: {'configurado' if mfa else 'pendiente'}")
