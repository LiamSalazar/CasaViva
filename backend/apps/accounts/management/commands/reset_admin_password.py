import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import revoke_user_sessions
from apps.audit.services import audit_event


class Command(BaseCommand):
    help = "Restablece de forma interactiva la contraseña de un administrador."

    def add_arguments(self, parser):
        parser.add_argument("email")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            user = User.objects.get(email__iexact=options["email"].strip())
        except User.DoesNotExist as exc:
            raise CommandError("No existe una cuenta con ese correo.") from exc
        first = getpass.getpass("Nueva contraseña: ")
        second = getpass.getpass("Confirma la nueva contraseña: ")
        if first != second:
            raise CommandError("Las contraseñas no coinciden.")
        validate_password(first, user=user)
        user.set_password(first)
        user.last_password_change_at = timezone.now()
        user.authz_version += 1
        user.save(update_fields=["password", "last_password_change_at", "authz_version", "updated_at"])
        revoke_user_sessions(user)
        audit_event(None, "PASSWORD_CHANGED", user, reason="Restablecimiento local mediante comando seguro")
        self.stdout.write(self.style.SUCCESS(f"Contraseña actualizada para {user.email}; MFA no fue modificado."))

