from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.catalog.models import Developer, Development, DevelopmentModel, HousingModel, PropertyOffering, PropertyType
from apps.common.models import SourceRecord
from apps.geo.models import State, Municipality
from apps.listings.models import AvailabilityRecord, Listing, PriceRecord
from apps.content.models import LocationContent


DATA = [
    # developer, development, municipality, state, model, price, type, construction, basis, land, beds, baths, parking, status, publish, variant, garden
    ("ARA", "Citara", "Huehuetoca", "Estado de México", "Ciprés", 1350000, "house", 67.10, "EXACT", None, 3, 1.5, 1, "AVAILABLE", True, None, None),
    ("ARA", "Citara", "Huehuetoca", "Estado de México", "Camelia", 1060000, "house", 46, "EXACT", 76, 2, 2, 1, "AVAILABLE", True, None, None),
    ("ARA", "Fuentes de Tizayuca II", "Tizayuca", "Hidalgo", "Gardenia", 823345, "apartment", 50, "EXACT", None, 2, 1, 1, "AVAILABLE", True, None, None),
    ("ARA", "Fuentes de Tizayuca II", "Tizayuca", "Hidalgo", "Alazán", 1230000, "house", 69.1, "EXACT", 67.4, 2, 1.5, 1, "AVAILABLE", True, None, None),
    ("ARA", "Fuentes de Tizayuca II", "Tizayuca", "Hidalgo", "Camelia", 988000, "house", 45.55, "EXACT", 72, 2, 2, 1, "AVAILABLE", True, None, None),
    ("ARA", "Fuentes de Tizayuca II", "Tizayuca", "Hidalgo", "Ciprés", 1280000, "house", 67.08, "EXACT", None, 3, 1.5, 1, "AVAILABLE", True, None, None),
    ("ARA", "Fuentes de Tizayuca II", "Tizayuca", "Hidalgo", "Lirio", None, "house", 70.47, "EXACT", None, 2, 2, 2, "SOLD", False, None, None),
    ("ARA", "Fuentes de Tizayuca II", "Tizayuca", "Hidalgo", "Manzanos", None, "house", 62.82, "EXACT", None, 2, 1.5, 1, "SOLD", False, None, None),
    ("ARA", "Imperio Real", "Otzolotepec", "Estado de México", "Granada", 1590000, "house", 73, "EXACT", 96, 3, 2, 2, "AVAILABLE", True, None, None),
    ("ARA", "Imperio Real", "Otzolotepec", "Estado de México", "Cedro", 1830202, "house", 87, "EXACT", None, 3, 3, 2, "AVAILABLE", True, None, None),
    ("ARA", "Imperio Real", "Otzolotepec", "Estado de México", "Tabachín", 1890000, "house", 94, "EXACT", None, 3, 2.5, 2, "AVAILABLE", True, None, 18),
    ("ARA", "Arona Residencial", "Zinacantepec", "Estado de México", "Aliso", 2850000, "house", 102, "EXACT", 120, 3, 2.5, 2, "AVAILABLE", True, None, 12),
    ("ARA", "Arona Residencial", "Zinacantepec", "Estado de México", "Siena", 3330000, "house", 120, "EXACT", None, 3, 2.5, 2, "AVAILABLE", True, None, 12),
    ("ARA", "La Escondida Residencial", "Ocoyoacac", "Estado de México", "Arce", 3600000, "house", 123, "EXACT", None, 3, 2.5, 2, "AVAILABLE", True, None, None),
    ("ARA", "La Escondida Residencial", "Ocoyoacac", "Estado de México", "Sauco", 4600000, "house", 157.12, "EXACT", None, 3, 2.5, 2, "AVAILABLE", True, None, None),
    ("ARA", "La Escondida Residencial", "Ocoyoacac", "Estado de México", "Sándalo", 4900000, "house", 167.29, "EXACT", None, 3, 2.5, 2, "AVAILABLE", True, None, None),
    ("Nuestro Hogar", "Vive Alto Zumpango", "Zumpango", "Estado de México", "Verona", 749000, "apartment", 50, "UP_TO", None, 2, 1, 1, "AVAILABLE", True, "Planta Baja", 57.03),
    ("Nuestro Hogar", "Vive Alto Zumpango", "Zumpango", "Estado de México", "Verona", 749000, "apartment", 50, "UP_TO", None, 2, 1, 1, "AVAILABLE", True, "Nivel 1–3", None),
    ("Nuestro Hogar", "Vive Alto Zumpango", "Zumpango", "Estado de México", "Génova", 890000, "apartment", 64, "UP_TO", None, 2, 1, 1, "AVAILABLE", True, "Planta Baja", 41.72),
    ("Nuestro Hogar", "Vive Alto Chalco", "Chalco", "Estado de México", "Verona", 799000, "apartment", 50, "UP_TO", None, 2, 1, 1, "AVAILABLE", True, None, None),
    ("Nuestro Hogar", "Vive Alto Chalco", "Chalco", "Estado de México", "Génova", 949000, "apartment", 65, "UP_TO", None, 2, 1, 1, "AVAILABLE", True, None, None),
    ("Nuestro Hogar", "Vive Alto Chalco", "Chalco", "Estado de México", "Capri", 1024000, "apartment", 78, "EXACT", None, 2, 1, 1, "AVAILABLE", True, "Planta Baja", None),
    ("Nuestro Hogar", "Vive Alto Chalco", "Chalco", "Estado de México", "Capri", 1024000, "apartment", 72, "EXACT", None, 2, 1, 1, "AVAILABLE", True, "Nivel 1–3", None),
]

SHARED = [
    ("Roma", 2, 1.5, None), ("Roma+", 3, 1.5, None), ("Milán", 2, 1.5, None), ("Milán+", 3, 1.5, None),
    ("Florencia", 2, 1.5, None), ("Venecia", 2, 1.5, 3), ("Nápoles", 3, 2.5, None), ("Nápoles+", 3, 2.5, None),
    ("Portofino", 3, 3.5, None), ("Portofino+", 3, 3.5, None),
]
IZTAC = [(1249000,69.36),(1417000,104.04),(1499000,82.36),(1729000,122.66),(1699000,90),(1849000,120),(2269000,125.84),(2583000,159.49),(3069000,178.70),(3599000,235.47)]
ZUMPANGO = [(1229000,69.36),(1389000,104.04),(1325000,82.36),(1475000,122.66),(1536000,90),(1635000,120),(2241000,125.84),(2514000,159.49),(2989000,178.70),(3582000,235.47)]


def slugify(value):
    import unicodedata, re
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value))


class Command(BaseCommand):
    help = "Crea el catálogo inmobiliario de referencia de agosto de 2026 sin sobrescribir registros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        observed = timezone.make_aware(datetime(2026, 8, 1, 12, 0))
        source, _ = SourceRecord.objects.get_or_create(source_name="Catálogo inicial CasaViva — referencias oficiales agosto 2026", defaults={"source_type": "MANUAL", "observed_at": observed, "notes": "Información inicial editable; campos no confirmados permanecen vacíos."})
        states = {}
        for name, code in [("Estado de México", "MEX"), ("Hidalgo", "HID"), ("Aguascalientes", "AGU")]:
            states[name], _ = State.objects.get_or_create(code=code, defaults={"name": name})
        devs = {}
        for name in ["ARA", "Nuestro Hogar", "DaVivir"]:
            devs[name], _ = Developer.all_objects.get_or_create(slug=slugify(name), defaults={"name": name})
        house = PropertyType.objects.get(code="house"); apartment = PropertyType.objects.get(code="apartment")
        all_rows = list(DATA)
        for development, municipality, state, prices in [("Residencial Iztac", "Chalco", "Estado de México", IZTAC), ("Nuevo Zumpango Residencial", "Zumpango", "Estado de México", ZUMPANGO)]:
            for (model, beds, baths, parking), (price, area) in zip(SHARED, prices):
                all_rows.append(("Nuestro Hogar", development, municipality, state, model, price, "house", area, "UP_TO", None, beds, baths, parking, "AVAILABLE", True, None, None))
        created = 0
        models = {}
        developments = {}
        for row in all_rows:
            developer_name, development_name, municipality_name, state_name, model_name, price, type_code, construction, basis, land, beds, baths, parking, availability, publish, variant, garden = row
            developer = devs[developer_name]; state = states[state_name]
            municipality, _ = Municipality.objects.get_or_create(state=state, name=municipality_name, defaults={"is_featured": True})
            dev_key = (developer_name, development_name)
            if dev_key not in developments:
                developments[dev_key], _ = Development.all_objects.get_or_create(slug=slugify(development_name), defaults={"developer": developer, "name": development_name, "state": state, "municipality": municipality, "is_active": True, "is_published": True})
            model_key = (developer_name, model_name)
            if model_key not in models:
                models[model_key], _ = HousingModel.all_objects.get_or_create(slug=f"{slugify(developer_name)}-{slugify(model_name)}", defaults={"developer": developer, "name": model_name})
            link, _ = DevelopmentModel.all_objects.get_or_create(development=developments[dev_key], housing_model=models[model_key], defaults={"is_active": True})
            reference = f"seed:{slugify(development_name)}:{slugify(model_name)}:{slugify(variant or 'base')}"
            offering, was_created = PropertyOffering.all_objects.get_or_create(internal_reference=reference, defaults={
                "promotion_authorized": True, "information_verified_at": observed,
                "source_type": "DEVELOPER", "condition": "NEW", "development_model": link, "variant_name": variant,
                "property_type": apartment if type_code == "apartment" else house,
                "bedrooms_min": beds, "bathrooms_total": baths, "parking_min": parking,
                "construction_area_max": construction if basis == "UP_TO" else None,
                "construction_area_min": construction if basis == "EXACT" else None,
                "construction_area_basis": basis, "land_area_min": land, "land_area_max": land,
                "land_area_basis": "EXACT" if land is not None else None,
                "garden_area_max": garden, "garden_area_basis": "UP_TO" if garden is not None else None,
            })
            if not was_created: continue
            created += 1
            if price is not None:
                PriceRecord.objects.create(offering=offering, price_type="FROM", amount_min=Decimal(str(price)), currency="MXN", effective_from=observed, source_record=source)
            AvailabilityRecord.objects.create(offering=offering, status=availability, effective_from=observed)
            suffix = f"-{slugify(variant)}" if variant else ""
            Listing.objects.create(offering=offering, title=f"{model_name}{' — ' + variant if variant else ''}", slug=f"{slugify(development_name)}-{slugify(model_name)}{suffix}", short_description=f"{model_name} en {development_name}", description="", is_published=bool(publish and price is not None), published_at=observed if publish and price is not None else None)
        # Entidades conocidas con asociaciones inciertas: no se inventan offerings.
        for development_name, municipality_name, state_name, names in [
            ("Bosques de Ibiza", "Tizayuca", "Hidalgo", ["Trento", "Ibiza 65", "Ibiza 97", "Mallorca"]),
            ("Montecarlo", "Tecámac", "Estado de México", ["Fortezza", "Mónaco", "Mónaco 3N"]),
            ("Colinas de San Patricio", "Aguascalientes", "Aguascalientes", ["Altamura", "Darian"]),
            ("Sonoma", "Aguascalientes", "Aguascalientes", []),
        ]:
            state = states[state_name]; municipality, _ = Municipality.objects.get_or_create(state=state, name=municipality_name, defaults={"is_featured": False})
            development, _ = Development.all_objects.get_or_create(slug=slugify(development_name), defaults={"developer": devs["DaVivir"], "name": development_name, "state": state, "municipality": municipality, "is_published": False})
            for name in names:
                model, _ = HousingModel.all_objects.get_or_create(slug=f"davivir-{slugify(name)}", defaults={"developer": devs["DaVivir"], "name": name})
                DevelopmentModel.all_objects.get_or_create(development=development, housing_model=model)
        for municipality in Municipality.objects.filter(is_featured=True).select_related("state"):
            base_slug = slugify(municipality.name)
            location_slug = base_slug if not LocationContent.all_objects.filter(slug=base_slug).exclude(municipality=municipality).exists() else f"{base_slug}-{slugify(municipality.state.code)}"
            LocationContent.all_objects.get_or_create(
                municipality=municipality,
                defaults={"slug": location_slug, "is_featured": True, "description": ""},
            )
        self.stdout.write(self.style.SUCCESS(f"Catálogo listo: {created} ofertas nuevas; registros existentes no se modificaron."))
