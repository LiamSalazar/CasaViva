import io
import os
import uuid
from urllib.request import Request, urlopen
from datetime import timedelta
from decimal import Decimal

from PIL import Image, ImageDraw
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import PermissionOverride, User
from apps.accounts.services import seed_groups
from apps.analytics.models import AnalyticsEvent, AnonymousVisitor, WebSession
from apps.audit.models import AuditEvent
from apps.catalog.models import Development, DevelopmentMedia, Developer, FeatureChoice, FeatureDefinition, HousingModel, PropertyOffering, PropertyType
from apps.content.models import Guide, HomeContent, HomeHeroSlide
from apps.crm.models import Inquiry, Lead, LeadInterest, LeadStageHistory, Sale, Visit
from apps.geo.models import Municipality
from apps.listings.models import AvailabilityRecord, Listing, ListingMedia, PriceRecord
from apps.marketing.models import MarketingCampaign, MarketingSpend
from apps.media_library.services import store_upload


NAMESPACE = uuid.UUID("6bc89a5c-274a-4c63-9eba-8e6525629120")

DEMO_PHOTO_URLS = [
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1400&q=82",  # exterior
    "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1400&q=82",  # sala
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1400&q=82",  # cocina
    "https://images.unsplash.com/photo-1600607688969-a5bfcd646154?auto=format&fit=crop&w=1400&q=82",  # recámara
    "https://images.unsplash.com/photo-1600573472550-8090b5e0745e?auto=format&fit=crop&w=1400&q=82",  # desarrollo
    "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1400&q=82",  # amenidades
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1400&q=82",
    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1400&q=82",
]


def stable(name):
    return uuid.uuid5(NAMESPACE, name)


def download_demo_photo(url):
    try:
        request = Request(url, headers={"User-Agent": "CasaViva demo seed/1.0"})
        with urlopen(request, timeout=3) as response:
            content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
            length = int(response.headers.get("Content-Length") or 0)
            if not content_type.startswith("image/") or length > 8 * 1024 * 1024:
                return None
            data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                return None
            return data, content_type
    except (OSError, ValueError):
        return None


class Command(BaseCommand):
    help = "Llena exclusivamente casaviva_demo con una operación inmobiliaria determinista y rica."

    @transaction.atomic
    def handle(self, *args, **options):
        from django.conf import settings
        if os.environ.get("CASAVIVA_MODE", "").lower() != "demo" or str(settings.DATABASES["default"]["NAME"]) != "casaviva_demo":
            raise CommandError("ABORTADO: seed_demo exige CASAVIVA_MODE=demo y la base exacta casaviva_demo.")
        password = os.environ.get("DEMO_OWNER_PASSWORD")
        totp_secret = os.environ.get("DEMO_TOTP_SECRET")
        if not password or not totp_secret:
            raise CommandError("DEMO_OWNER_PASSWORD y DEMO_TOTP_SECRET son obligatorios.")

        call_command("seed_system")
        owner_group, _ = seed_groups()
        role_names = ["Founder Admin", "Operaciones e inventario", "Comercial", "Marketing y BI", "Contenido"]
        users = []
        for index, (email, name, role) in enumerate([
            ("owner@example.test", "Liam Demo", "Owner"),
            ("ana@example.test", "Ana Demo", "Comercial"),
            ("alfredo@example.test", "Alfredo Demo", "Operaciones e inventario"),
            ("marketing@example.test", "Mariana Demo", "Marketing y BI"),
            ("contenido@example.test", "Claudia Demo", "Contenido"),
        ]):
            first, last = name.split(" ", 1)
            user, _ = User.objects.get_or_create(email=email, defaults={"first_name": first, "last_name": last})
            user.first_name, user.last_name, user.is_active = first, last, True
            user.is_superuser = role == "Owner"; user.is_staff = role == "Owner"; user.set_password(password); user.save()
            group = owner_group if role == "Owner" else __import__("django.contrib.auth.models", fromlist=["Group"]).Group.objects.get(name=role)
            user.groups.set([group]); TOTPDevice.objects.update_or_create(user=user, name="Demo", defaults={"key": totp_secret, "confirmed": True})
            users.append(user)
        denied = Permission.objects.get(content_type__app_label="analytics", codename="view_bi")
        PermissionOverride.objects.update_or_create(user=users[3], permission=denied, defaults={"effect": "DENY", "created_by": users[0]})

        municipality = Municipality.objects.select_related("state").first()
        if not municipality:
            raise CommandError("Ejecuta seed_reference_catalog antes de seed_demo.")
        for index in range(5):
            Developer.all_objects.get_or_create(slug=f"demo-desarrolladora-{index+1}", defaults={"name": f"Desarrolladora Demo {index+1}", "is_active": True, "created_by": users[0], "updated_by": users[0]})
        developers = list(Developer.objects.order_by("name")[:5])
        for index in range(10):
            developer = developers[index % len(developers)]
            development, _ = Development.all_objects.get_or_create(slug=f"residencial-demo-{index+1}", defaults={"developer": developer, "name": f"Residencial Demo {index+1}", "state": municipality.state, "municipality": municipality, "is_active": True, "is_published": index < 8, "created_by": users[0], "updated_by": users[0]})
            model, _ = HousingModel.all_objects.get_or_create(slug=f"modelo-demo-{index+1}", defaults={"developer": developer, "name": f"Modelo Demo {index+1}", "created_by": users[0], "updated_by": users[0]})
            __import__("apps.catalog.models", fromlist=["DevelopmentModel"]).DevelopmentModel.all_objects.get_or_create(development=development, housing_model=model, defaults={"created_by": users[0], "updated_by": users[0]})

        feature_specs = [("demo-bool", "Paneles solares", "BOOLEAN"), ("demo-number", "Altura libre", "NUMBER"), ("demo-text", "Acabado especial", "TEXT"), ("demo-choice", "Orientación", "CHOICE")]
        for code, label, kind in feature_specs:
            feature, _ = FeatureDefinition.objects.update_or_create(code=code, defaults={"label": label, "category": "Demo", "data_type": kind, "unit": "m" if kind == "NUMBER" else None, "is_public": True, "is_filterable": kind != "TEXT", "is_active": True})
            if kind == "CHOICE":
                for order, label_value in enumerate(["Norte", "Sur", "Oriente", "Poniente"]):
                    FeatureChoice.objects.update_or_create(definition=feature, value=label_value.lower(), defaults={"label": label_value, "sort_order": order})

        property_type = PropertyType.objects.first()
        while PropertyOffering.all_objects.count() < 60:
            index = PropertyOffering.all_objects.count() + 1
            offering = PropertyOffering.all_objects.create(source_type="PRIVATE", condition="USED" if index % 3 else "NEW", property_type=property_type, state=municipality.state, municipality=municipality, internal_reference=f"DEMO-PART-{index:03d}", bedrooms_min=2 + index % 3, bathrooms_total=1 + index % 2, construction_area_min=Decimal(60 + index), created_by=users[0], updated_by=users[0])
            listing = Listing.all_objects.create(offering=offering, title=f"Propiedad demostración {index}", slug=f"propiedad-demostracion-{index}", short_description="Inventario simulado de CasaViva.", description="Propiedad sintética creada exclusivamente para el modo demostración.", is_published=index % 5 != 0, is_featured=index % 11 == 0, published_at=timezone.now() if index % 5 else None, created_by=users[0], updated_by=users[0])
            old = timezone.now() - timedelta(days=90)
            PriceRecord.objects.create(offering=offering, price_type="FIXED", amount_min=Decimal(900000 + index * 25000), currency="MXN", effective_from=old, effective_to=old + timedelta(days=55), created_by=users[0])
            PriceRecord.objects.create(offering=offering, price_type="FIXED", amount_min=Decimal(950000 + index * 25000), currency="MXN", effective_from=old + timedelta(days=55), created_by=users[0])
            AvailabilityRecord.objects.create(offering=offering, status="AVAILABLE", effective_from=old, effective_to=old + timedelta(days=70), changed_by=users[0])
            status = ["AVAILABLE", "RESERVED", "SOLD", "TEMPORARILY_UNAVAILABLE"][index % 4]
            AvailabilityRecord.objects.create(offering=offering, status=status, effective_from=old + timedelta(days=70), changed_by=users[0])
            if index % 13 == 0:
                listing.archived_at = timezone.now() - timedelta(days=4); listing.archived_by = users[0]; listing.save(update_fields=["archived_at", "archived_by"])

        assets = []
        colors = [(224,216,204), (196,203,197), (210,198,187), (184,192,204), (218,208,190), (198,184,175), (205,194,181), (190,202,205)]
        for index, url in enumerate(DEMO_PHOTO_URLS):
            key = f"demo-photo-{index}"
            existing = __import__("apps.media_library.models", fromlist=["MediaAsset"]).MediaAsset.objects.filter(alt_text=key).first()
            if existing: assets.append(existing); continue
            downloaded = download_demo_photo(url)
            if downloaded:
                photo_bytes, content_type = downloaded
                extension = "jpg" if content_type in {"image/jpeg", "image/jpg"} else "png"
                filename = f"{key}.{extension}"
            else:
                image = Image.new("RGB", (1200, 760), colors[index]); draw = ImageDraw.Draw(image); draw.rectangle((90, 100, 1110, 660), outline=(55,55,55), width=5); draw.rectangle((160, 190, 560, 590), fill=(245,242,236)); draw.rectangle((640, 190, 1040, 590), fill=(235,232,225)); draw.line((600,100,600,660), fill=(55,55,55), width=3)
                output = io.BytesIO(); image.save(output, format="PNG"); photo_bytes = output.getvalue(); filename = f"{key}.png"
            upload = SimpleUploadedFile(filename, photo_bytes, content_type=content_type if downloaded else "image/png")
            assets.append(store_upload(upload, users[0], media_type="IMAGE", alt_text=key))
        floorplan_key = "demo-floorplan"
        floorplan = __import__("apps.media_library.models", fromlist=["MediaAsset"]).MediaAsset.objects.filter(alt_text=floorplan_key).first()
        if not floorplan:
            image = Image.new("RGB", (1200, 760), (238, 235, 226)); draw = ImageDraw.Draw(image); draw.rectangle((90, 100, 1110, 660), outline=(55,55,55), width=5); draw.line((600,100,600,660), fill=(55,55,55), width=3); draw.line((90,380,1110,380), fill=(55,55,55), width=3)
            output = io.BytesIO(); image.save(output, format="PNG")
            floorplan = store_upload(SimpleUploadedFile("demo-floorplan.png", output.getvalue(), content_type="image/png"), users[0], media_type="FLOORPLAN", alt_text=floorplan_key)
        demo_listings = list(Listing.objects.filter(slug__startswith="propiedad-demostracion-").order_by("slug"))
        for index, listing in enumerate(demo_listings):
            ListingMedia.objects.get_or_create(listing=listing, media=assets[index % len(assets)], defaults={"role": "HERO", "sort_order": 0})
            ListingMedia.objects.get_or_create(listing=listing, media=assets[(index + 1) % len(assets)], defaults={"role": "GALLERY", "sort_order": 1})
            ListingMedia.objects.get_or_create(listing=listing, media=floorplan, defaults={"role": "FLOORPLAN", "sort_order": 2})
        demo_developments = list(Development.objects.filter(slug__startswith="residencial-demo-").order_by("slug"))
        for index, development in enumerate(demo_developments):
            DevelopmentMedia.objects.get_or_create(development=development, media=assets[index % len(assets)], defaults={"role": "HERO", "sort_order": 0})
            DevelopmentMedia.objects.get_or_create(development=development, media=assets[(index + 2) % len(assets)], defaults={"role": "GALLERY", "sort_order": 1})

        today = timezone.localdate()
        channels = [("INSTAGRAM","instagram","paid_social"),("FACEBOOK","facebook","paid_social"),("TIKTOK","tiktok","paid_social"),("GOOGLE","google","paid_search")]
        campaigns = []
        for index in range(10):
            channel, source, medium = channels[index % len(channels)]
            campaign, _ = MarketingCampaign.all_objects.update_or_create(utm_campaign=f"demo_campana_{index+1:02d}", defaults={"name": f"Campaña demostración {index+1}", "channel": channel, "planned_budget": Decimal(10000 + index * 2000), "utm_source": source, "utm_medium": medium, "default_landing_path": "/propiedades", "start_date": today - timedelta(days=90-index*5), "end_date": None, "is_active": index < 8, "notes": "Datos simulados.", "created_by": users[0], "updated_by": users[0]})
            campaigns.append(campaign)
            for part in range(3):
                MarketingSpend.objects.update_or_create(id=stable(f"spend-{index}-{part}"), defaults={"campaign": campaign, "date": today - timedelta(days=75-index*4-part*7), "amount": Decimal(900 + index*100 + part*175), "currency": "MXN"})

        leads = []
        listings = list(
            Listing.objects.filter(slug__startswith="propiedad-demostracion-")
            .select_related("offering")
            .order_by("slug")
        )
        for index in range(72):
            lead, _ = Lead.all_objects.update_or_create(id=stable(f"lead-{index}"), defaults={"first_name": f"Cliente {index+1}", "last_name": "Demostración", "email": f"cliente{index+1}@example.test", "phone_raw": f"555100{index:04d}", "phone_normalized": f"52555100{index:04d}", "status": "WON" if index < 12 else "LOST" if index < 20 else ["NEW","CONTACTED","INTERESTED","VISIT_SCHEDULED","NEGOTIATING"][index % 5], "owner_user": users[1], "first_source": channels[index % 4][1], "created_by": users[0], "updated_by": users[0]})
            age = [3, 12, 26, 48, 78][index % 5]; Lead.all_objects.filter(pk=lead.pk).update(created_at=timezone.now()-timedelta(days=age)); lead.refresh_from_db(); leads.append(lead)
            LeadStageHistory.objects.update_or_create(lead=lead, ended_at__isnull=True, defaults={"stage": lead.status, "started_at": lead.created_at, "changed_by": users[1]})
            LeadInterest.objects.update_or_create(id=stable(f"interest-{index}"), defaults={"lead": lead, "offering": listings[index % len(listings)].offering, "interest_type": ["VIEWED","FAVORITED","INQUIRED","VISITED"][index % 4]})

        visitors = []
        for index in range(220):
            started = timezone.now() - timedelta(days=(index * 7) % 90, hours=index % 24)
            visitor, _ = AnonymousVisitor.objects.update_or_create(id=stable(f"visitor-{index}"), defaults={"first_seen_at": started, "last_seen_at": started+timedelta(minutes=8)})
            campaign_index = index % 9  # campaña 10: gasto y cero tráfico
            lead = leads[index % len(leads)] if index < 150 else None
            session, _ = WebSession.objects.update_or_create(id=stable(f"session-{index}"), defaults={"visitor": visitor, "lead": lead, "started_at": started, "last_seen_at": started+timedelta(minutes=8), "utm_source": campaigns[campaign_index].utm_source, "utm_medium": campaigns[campaign_index].utm_medium, "utm_campaign": campaigns[campaign_index].utm_campaign, "utm_content": f"reel_{index%6:02d}", "landing_path": "/propiedades", "device_category": "mobile" if index%3 else "desktop", "consent_state": "granted"})
            for event_index, event_name in enumerate(["page_viewed", "search_performed", "listing_viewed"]):
                listing = listings[index % len(listings)] if event_name == "listing_viewed" else None
                AnalyticsEvent.objects.update_or_create(id=stable(f"event-{index}-{event_index}"), defaults={"occurred_at": started+timedelta(minutes=event_index+1), "event_name": event_name, "schema_version": 1, "visitor": visitor, "session": session, "lead": lead, "listing": listing, "offering": listing.offering if listing else None, "page_path": listing and f"/propiedades/{listing.slug}" or "/propiedades", "properties": {"result_count": 24} if event_name == "search_performed" else {}})
            visitors.append(visitor)

        for index in range(88):
            lead = leads[index % len(leads)]; session = WebSession.objects.filter(lead=lead).order_by("started_at").first()
            Inquiry.objects.update_or_create(id=stable(f"inquiry-{index}"), defaults={"lead": lead, "listing": listings[index % len(listings)], "channel": "WEB", "intent": "INFORMATION" if index%3 else "VISIT_REQUEST", "message": "Consulta simulada para demostrar seguimiento.", "session_id": session.id if session else None, "status": ["NEW","VIEWED","ATTENDED"][index%3], "assigned_to": users[1]})
        for index in range(36):
            lead = leads[index]; scheduled = timezone.now()-timedelta(days=(index*5)%85)
            status = "NO_SHOW" if index == 3 else "CANCELLED" if index%9 == 0 else "COMPLETED" if index < 28 else "SCHEDULED"
            Visit.objects.update_or_create(id=stable(f"visit-{index}"), defaults={"lead": lead, "offering": listings[index % len(listings)].offering, "scheduled_at": scheduled, "status": status, "completed_at": scheduled+timedelta(hours=1) if status == "COMPLETED" else None, "assigned_to": users[1], "notes": "Visita de demostración."})
        for index in range(14):
            price = Decimal(1200000 + index*85000); status = "CANCELLED" if index == 13 else "CLOSED"
            Sale.objects.update_or_create(id=stable(f"sale-{index}"), defaults={"lead": leads[index], "offering": listings[index % len(listings)].offering, "listing": listings[index % len(listings)], "sale_price": price, "commission_rate": Decimal("3.00"), "commission_amount": price*Decimal("0.03"), "closed_at": timezone.now()-timedelta(days=index*6+2), "status": status, "created_by": users[1]})

        home, _ = HomeContent.all_objects.update_or_create(key="main", defaults={"hero_eyebrow": "México · selección demostrativa", "hero_title": "Espacios para una vida extraordinaria", "editorial_title": "CasaViva en operación", "editorial_body": "Datos simulados para recorrer la experiencia completa.", "editorial_media": assets[0], "created_by": users[0], "updated_by": users[0]})
        for index, listing in enumerate(listings[:5]):
            HomeHeroSlide.all_objects.update_or_create(home_content=home, listing=listing, defaults={"sort_order": index, "is_active": True, "created_by": users[0], "updated_by": users[0]})
        for index in range(8):
            Guide.all_objects.update_or_create(slug=f"guia-demo-{index+1}", defaults={"title": f"Guía CasaViva {index+1}", "excerpt": "Orientación inmobiliaria para clientes.", "content": "Contenido editorial simulado del modo demostración.", "category": "Mercado", "hero_media": assets[index%4], "is_published": True, "is_featured": index < 3, "published_at": timezone.now()-timedelta(days=index*9), "created_by": users[4], "updated_by": users[4]})
        for index in range(30):
            AuditEvent.objects.get_or_create(id=stable(f"audit-{index}"), defaults={"actor_user": users[index%len(users)], "action": ["CREATE","UPDATE","PRICE_CHANGE","AVAILABILITY_CHANGE","PUBLISH"][index%5], "entity_type": "Listing", "entity_id": str(listings[index%len(listings)].id), "old_values": {"amount_min": 1200000+index*1000}, "new_values": {"amount_min": 1250000+index*1000}, "success": True, "reason": "Actividad simulada"})
        self.stdout.write(self.style.SUCCESS(f"Demo lista: {Developer.objects.count()} desarrolladoras, {Development.objects.count()} desarrollos, {HousingModel.objects.count()} modelos, {PropertyOffering.objects.count()} propiedades, {Lead.objects.count()} clientes, {Inquiry.objects.count()} consultas, {Visit.objects.count()} visitas y {Sale.objects.count()} ventas."))
