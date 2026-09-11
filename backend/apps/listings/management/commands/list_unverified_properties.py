from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Lista propiedades que requieren revisión; nunca autoriza ni publica automáticamente."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Incluye también propiedades verificadas")

    def handle(self, *args, **options):
        queryset = Listing.all_objects.select_related(
            "offering__development_model__development__developer"
        ).order_by("title")
        if not options["all"]:
            queryset = queryset.filter(
                Q(offering__promotion_authorized=False) | Q(offering__information_verified_at__isnull=True)
            )
        self.stdout.write("property\tprovider\tpublished\tpromotion_authorized\tinformation_verified_at")
        for listing in queryset:
            offering = listing.offering
            provider = offering.public_provider_label or (
                offering.development_model.development.developer.name if offering.development_model_id else "Particular"
            )
            self.stdout.write(
                f"{listing.title}\t{provider}\t{listing.is_published}\t"
                f"{offering.promotion_authorized}\t{offering.information_verified_at or ''}"
            )
