import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import seed_groups
from apps.catalog.models import PropertyOffering, PropertyType
from apps.geo.models import Municipality
from apps.listings.models import AvailabilityRecord, Listing, PriceRecord


class Command(BaseCommand):
    help = "Crea usuarios aislados para Playwright; sólo funciona contra la base de pruebas."

    def handle(self, *args, **options):
        database_name = settings.DATABASES["default"]["NAME"]
        if "test" not in database_name.lower() or os.environ.get("CASAVIVA_E2E") != "1":
            raise CommandError("setup_e2e sólo puede ejecutarse con CASAVIVA_E2E=1 contra una BD cuyo nombre contenga 'test'.")
        password = os.environ.get("E2E_ADMIN_PASSWORD")
        totp_secret = os.environ.get("E2E_TOTP_SECRET")
        if not password or not totp_secret or len(totp_secret) < 32:
            raise CommandError("E2E_ADMIN_PASSWORD y E2E_TOTP_SECRET (>=32 caracteres hex) son obligatorios.")

        owner, founder = seed_groups()
        fixtures = [
            ("liam@example.test", "Liam", True, owner),
            ("ana@example.test", "Ana", False, founder),
            ("alfredo@example.test", "Alfredo", False, founder),
            ("attribution@example.test", "Atribución", False, founder),
            ("catalog@example.test", "Catálogo", False, founder),
            ("marketing@example.test", "Marketing", False, founder),
            ("content@example.test", "Contenido", False, founder),
            ("geo@example.test", "Geo", False, founder),
        ]
        for email, first_name, is_owner, group in fixtures:
            user, _ = User.objects.get_or_create(email=email, defaults={"first_name": first_name})
            user.first_name = first_name
            user.is_active = True
            user.is_staff = is_owner
            user.is_superuser = is_owner
            user.set_password(password)
            user.save()
            user.groups.set([group])
            TOTPDevice.objects.filter(user=user).delete()
            TOTPDevice.objects.create(user=user, name="Playwright", key=totp_secret, confirmed=True)
        owner_user = User.objects.get(email="liam@example.test")
        municipality = Municipality.objects.select_related("state").first()
        if municipality:
            property_type, _ = PropertyType.objects.get_or_create(
                code="duplex", defaults={"name": "Dúplex", "sort_order": 99}
            )
            for index in range(30):
                reference = f"E2E-DUPLEX-{index:02d}"
                offering, _ = PropertyOffering.objects.get_or_create(
                    internal_reference=reference,
                    defaults={
                        "source_type": "PRIVATE", "condition": "USED",
                        "property_type": property_type, "state": municipality.state,
                        "municipality": municipality, "bedrooms_min": 3,
                        "bathrooms_total": 2, "levels_min": 2,
                        "created_by": owner_user, "updated_by": owner_user,
                    },
                )
                listing, _ = Listing.objects.get_or_create(
                    offering=offering,
                    defaults={
                        "title": f"Dúplex E2E {index + 1}", "slug": f"duplex-e2e-{index + 1}",
                        "short_description": "Inventario aislado para pruebas de integración.",
                        "description": "Propiedad generada exclusivamente en casaviva_test.",
                        "is_published": True, "published_at": timezone.now(),
                        "created_by": owner_user, "updated_by": owner_user,
                    },
                )
                if not offering.prices.filter(effective_to__isnull=True).exists():
                    PriceRecord.objects.create(
                        offering=offering, price_type="FIXED", amount_min=1_000_000 + index * 10_000,
                        currency="MXN", effective_from=timezone.now(), created_by=owner_user,
                    )
                if not offering.availability_history.filter(effective_to__isnull=True).exists():
                    AvailabilityRecord.objects.create(
                        offering=offering, status="AVAILABLE", effective_from=timezone.now(), changed_by=owner_user,
                    )
        self.stdout.write(self.style.SUCCESS("Usuarios E2E aislados listos."))
