from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.services import seed_groups
from apps.catalog.models import Amenity, FeatureDefinition, PropertyType
from apps.crm.models import PrivacyNoticeVersion
import hashlib
from datetime import datetime


class Command(BaseCommand):
    help = "Crea roles, permisos y catálogos controlados iniciales sin sobrescribir cambios humanos."

    @transaction.atomic
    def handle(self, *args, **options):
        seed_groups()
        for order, (code, name) in enumerate([("house", "Casa"), ("apartment", "Departamento"), ("land", "Terreno"), ("townhouse", "Townhouse")]):
            PropertyType.objects.get_or_create(code=code, defaults={"name": name, "sort_order": order})
        for order, (name, category) in enumerate([
            ("Áreas verdes", "DEVELOPMENT"), ("Juegos infantiles", "DEVELOPMENT"),
            ("Acceso controlado", "SERVICE"), ("Jardín", "EXTERIOR"),
            ("Balcón", "EXTERIOR"), ("Bodega", "INTERIOR"), ("Cuarto de lavado", "INTERIOR"),
            ("Patio de servicio", "EXTERIOR"), ("Vestidor", "INTERIOR"),
        ]):
            slug = name.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace(" ", "-")
            Amenity.objects.get_or_create(slug=slug, defaults={"name": name, "category": category, "sort_order": order})
        FeatureDefinition.objects.get_or_create(code="area-tv-home-office", defaults={"label": "Área de TV / Home Office", "category": "Interior", "data_type": "BOOLEAN", "is_public": True})
        if not PrivacyNoticeVersion.objects.filter(is_active=True).exists():
            current_notice = (
                "CasaViva trata la información proporcionada para atender consultas, coordinar visitas y dar seguimiento a solicitudes inmobiliarias.\n"
                "Los formularios solicitan únicamente los datos necesarios para responder. El consentimiento y la versión del aviso aplicable se conservan como parte del historial de atención."
            )
            PrivacyNoticeVersion.objects.get_or_create(
                version="web-2026-08-01",
                defaults={"published_at": timezone.make_aware(datetime(2026, 8, 1, 0, 0)), "content_hash": hashlib.sha256(current_notice.encode()).hexdigest(), "is_active": True},
            )
        self.stdout.write(self.style.SUCCESS("Catálogos y roles iniciales listos."))
