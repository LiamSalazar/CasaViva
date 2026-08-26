import os
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.analytics.models import AnalyticsEvent, WebSession, AnonymousVisitor
from apps.crm.models import ConsentRecord, Inquiry, LeadInterest, LeadStageHistory, Visit, Sale, Lead
from apps.listings.models import AvailabilityRecord, PriceRecord, Listing
from apps.catalog.models import PropertyOffering, DevelopmentModel, HousingModel, Development, Developer
from apps.catalog.models import DevelopmentMedia
from apps.listings.models import ListingMedia
from apps.marketing.models import MarketingCampaign, MarketingSpend
from apps.content.models import Guide, HomeContent, HomeHeroSlide, LocationContent
from apps.audit.models import AuditEvent


class Command(BaseCommand):
    help = "Elimina datos demo sólo en desarrollo y vuelve a ejecutar los seeds seguros."

    @transaction.atomic
    def handle(self, *args, **options):
        database_name = str(settings.DATABASES["default"]["NAME"])
        if os.environ.get("CASAVIVA_MODE", "").lower() != "demo" or database_name != "casaviva_demo":
            raise CommandError("ABORTADO: reset_demo_data exige CASAVIVA_MODE=demo y la base exacta casaviva_demo.")
        for model in [AuditEvent, AnalyticsEvent, WebSession, AnonymousVisitor, ConsentRecord, Sale, Visit, LeadInterest, Inquiry, LeadStageHistory, Lead, MarketingSpend, MarketingCampaign, HomeHeroSlide, Guide, HomeContent, LocationContent, ListingMedia, DevelopmentMedia, Listing, AvailabilityRecord, PriceRecord, PropertyOffering, DevelopmentModel, HousingModel, Development, Developer]:
            getattr(model, "all_objects", model.objects).all().delete()
        call_command("seed_system")
        call_command("seed_reference_catalog")
        call_command("seed_demo")
        self.stdout.write(self.style.SUCCESS("Datos demo restablecidos."))
