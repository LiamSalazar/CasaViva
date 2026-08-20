import getpass
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from apps.accounts.models import User
from apps.accounts.services import seed_groups


class Command(BaseCommand):
    help = "Crea de forma segura a Liam, Ana y Alfredo. Acepta variables de entorno o entrada interactiva."

    def value(self, key, prompt, secret=False, default=None):
        value = os.environ.get(key)
        if value: return value
        if not os.isatty(0):
            if default is not None: return default
            raise CommandError(f"Falta {key}; en modo no interactivo debe proporcionarse por variable de entorno.")
        value = getpass.getpass(prompt) if secret else input(prompt)
        return value or default

    @transaction.atomic
    def handle(self, *args, **options):
        owner, founder = seed_groups()
        definitions = [
            ("LIAM", True, owner, self.value("LIAM_NAME", "Nombre de Liam: ", default="Liam")),
            ("ANA", False, founder, "Ana"),
            ("ALFREDO", False, founder, "Alfredo"),
        ]
        for prefix, superuser, group, name in definitions:
            email = self.value(f"{prefix}_EMAIL", f"Correo de {name}: ")
            password = self.value(f"{prefix}_PASSWORD", f"Contraseña inicial de {name}: ", secret=True)
            validate_password(password)
            if User.objects.filter(email__iexact=email).exists():
                self.stdout.write(f"{name}: ya existe; no se modificó.")
                continue
            user = User.objects.create_user(email=email, password=password, first_name=name, is_staff=superuser, is_superuser=superuser)
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(f"{name}: usuario creado; MFA será obligatorio al primer acceso."))
