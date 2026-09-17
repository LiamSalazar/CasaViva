import os
from base64 import b64decode

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import seed_groups
from apps.catalog.models import DevelopmentMedia, DevelopmentModel, PropertyOffering, PropertyType
from apps.content.models import Guide, LocationContent
from apps.geo.models import Municipality
from apps.listings.models import AvailabilityRecord, Listing, ListingMedia, PriceRecord
from apps.media_library.models import MediaAsset


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
            ("content-limited@example.test", "Contenido limitado", False, None),
            ("geo@example.test", "Geo", False, founder),
            ("mfa@example.test", "MFA", False, founder),
        ]
        content_group = Group.objects.get(name="Contenido")
        for email, first_name, is_owner, group in fixtures:
            user, _ = User.objects.get_or_create(email=email, defaults={"first_name": first_name})
            user.first_name = first_name
            user.is_active = True
            user.is_staff = is_owner
            user.is_superuser = is_owner
            user.set_password(password)
            user.save()
            user.groups.set([content_group if group is None else group])
            TOTPDevice.objects.filter(user=user).delete()
            TOTPDevice.objects.create(user=user, name="Playwright", key=totp_secret, confirmed=True)
        owner_user = User.objects.get(email="liam@example.test")
        for index in range(30):
            Guide.objects.get_or_create(
                slug=f"guia-publica-e2e-{index:02d}",
                defaults={
                    "title": f"Guía pública E2E {index:02d}",
                    "excerpt": "Contenido editorial aislado para paginación.",
                    "content": "Guía creada exclusivamente en casaviva_test.",
                    "category": "hogar",
                    "is_published": True,
                    "published_at": timezone.now(),
                    "created_by": owner_user,
                    "updated_by": owner_user,
                },
            )
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
                offering.promotion_authorized = True
                offering.information_verified_at = offering.information_verified_at or timezone.now()
                offering.save(update_fields=["promotion_authorized", "information_verified_at", "updated_at"])
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
            development_model = (
                DevelopmentModel.objects.select_related("development")
                .filter(development__is_published=True, development__archived_at__isnull=True)
                .order_by("development__slug", "created_at")
                .first()
            )
            if development_model:
                for index in range(30):
                    reference = f"E2E-DEVELOPMENT-{index:02d}"
                    offering, _ = PropertyOffering.objects.get_or_create(
                        internal_reference=reference,
                        defaults={
                            "source_type": "DEVELOPER", "condition": "NEW",
                            "development_model": development_model,
                            "property_type": property_type, "bedrooms_min": 3,
                            "bathrooms_total": 2, "levels_min": 2,
                            "created_by": owner_user, "updated_by": owner_user,
                        },
                    )
                    offering.promotion_authorized = True
                    offering.information_verified_at = offering.information_verified_at or timezone.now()
                    if offering.development_model_id != development_model.id:
                        offering.development_model = development_model
                    offering.save(
                        update_fields=[
                            "development_model", "promotion_authorized",
                            "information_verified_at", "updated_at",
                        ]
                    )
                    development_listing, _ = Listing.objects.get_or_create(
                        offering=offering,
                        defaults={
                            "title": f"Inventario desarrollo E2E {index + 1}",
                            "slug": f"inventario-desarrollo-e2e-{index + 1}",
                            "short_description": "Inventario completo aislado para E2E.",
                            "description": "Propiedad generada exclusivamente en casaviva_test.",
                            "is_published": True, "published_at": timezone.now(),
                            "created_by": owner_user, "updated_by": owner_user,
                        },
                    )
                    if not development_listing.is_published or development_listing.archived_at is not None:
                        development_listing.is_published = True
                        development_listing.archived_at = None
                        development_listing.published_at = development_listing.published_at or timezone.now()
                        development_listing.save(
                            update_fields=["is_published", "archived_at", "published_at", "updated_at"]
                        )
                    if not offering.prices.filter(effective_to__isnull=True).exists():
                        PriceRecord.objects.create(
                            offering=offering, price_type="FIXED",
                            amount_min=1_200_000 + index * 10_000, currency="MXN",
                            effective_from=timezone.now(), created_by=owner_user,
                        )
                    if not offering.availability_history.filter(effective_to__isnull=True).exists():
                        AvailabilityRecord.objects.create(
                            offering=offering, status="AVAILABLE",
                            effective_from=timezone.now(), changed_by=owner_user,
                        )
            gallery_listing = Listing.objects.get(slug="duplex-e2e-1")
            png = b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGPkEpFjYGBgYmBgYGBgAAAC5gBAXKUgWwAAAABJRU5ErkJggg=="
            )
            development_assets = []
            for role, media_type, filename, digest in (
                ("HERO", "IMAGE", "e2e/property-hero.png", "1" * 64),
                ("GALLERY", "IMAGE", "e2e/property-gallery.png", "2" * 64),
                ("FLOORPLAN", "FLOORPLAN", "e2e/property-floorplan.png", "3" * 64),
            ):
                if not default_storage.exists(filename):
                    default_storage.save(filename, ContentFile(png))
                asset, _ = MediaAsset.objects.get_or_create(
                    storage_key=filename,
                    defaults={
                        "media_type": media_type,
                        "original_filename": filename.rsplit("/", 1)[-1],
                        "mime_type": "image/png",
                        "byte_size": len(png),
                        "width": 2,
                        "height": 2,
                        "sha256": digest,
                        "alt_text": f"{role.title()} E2E",
                        "uploaded_by": owner_user,
                    },
                )
                ListingMedia.objects.get_or_create(
                    listing=gallery_listing,
                    media=asset,
                    defaults={"role": role, "sort_order": 0 if role == "HERO" else 1},
                )
                if role in ("HERO", "GALLERY"):
                    development_assets.append((role, asset))
            if development_model:
                for index, (role, asset) in enumerate(development_assets):
                    DevelopmentMedia.objects.get_or_create(
                        development=development_model.development,
                        media=asset,
                        defaults={"role": role, "sort_order": index},
                    )
            location_asset = development_assets[0][1]
            for index in range(8):
                location_municipality, _ = Municipality.objects.get_or_create(
                    state=municipality.state,
                    name=f"Ubicación E2E {index + 1}",
                    defaults={"is_active": True},
                )
                LocationContent.all_objects.update_or_create(
                    municipality=location_municipality,
                    defaults={
                        "slug": f"ubicacion-e2e-{index + 1}",
                        "description": "Ubicación destacada para probar el carrusel público.",
                        "hero_media": location_asset,
                        "is_featured": True,
                        "latitude": 19.4 + index * 0.01,
                        "longitude": -99.2 + index * 0.01,
                        "archived_at": None,
                        "created_by": owner_user,
                        "updated_by": owner_user,
                    },
                )
        self.stdout.write(self.style.SUCCESS("Usuarios E2E aislados listos."))
