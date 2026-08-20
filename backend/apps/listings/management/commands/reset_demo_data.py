from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.analytics.models import AnalyticsEvent, WebSession, AnonymousVisitor
from apps.crm.models import ConsentRecord, Inquiry, LeadInterest, LeadStageHistory, Visit, Sale, Lead
from apps.listings.models import AvailabilityRecord, PriceRecord, Listing
from apps.catalog.models import PropertyOffering, DevelopmentModel, HousingModel, Development, Developer


class Command(BaseCommand):
    help = "Elimina datos demo sólo en desarrollo y vuelve a ejecutar los seeds seguros."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or settings.__class__.__module__.endswith("production"):
            raise CommandError("reset_demo_data sólo está disponible en desarrollo.")
        for model in [AnalyticsEvent, WebSession, AnonymousVisitor, ConsentRecord, Sale, Visit, LeadInterest, Inquiry, LeadStageHistory, Lead, Listing, AvailabilityRecord, PriceRecord, PropertyOffering, DevelopmentModel, HousingModel, Development, Developer]:
            getattr(model, "all_objects", model.objects).all().delete()
        call_command("seed_system")
        call_command("seed_reference_catalog")
        self.stdout.write(self.style.SUCCESS("Datos demo restablecidos."))
