from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import BusinessModel, UUIDTimeStampedModel, SourceRecord
from apps.catalog.models import PropertyOffering
from apps.media_library.models import MediaAsset


class PriceRecord(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        FIXED = "FIXED", "Precio fijo"
        FROM = "FROM", "Desde"
        RANGE = "RANGE", "Rango"
        ON_REQUEST = "ON_REQUEST", "Precio a consultar"

    class Currency(models.TextChoices):
        MXN = "MXN", "Peso mexicano"

    offering = models.ForeignKey(PropertyOffering, on_delete=models.PROTECT, related_name="prices")
    price_type = models.CharField(max_length=15, choices=Type.choices)
    amount_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    amount_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.MXN)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    source_record = models.ForeignKey(SourceRecord, null=True, blank=True, on_delete=models.SET_NULL)
    observations = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["offering"], condition=Q(effective_to__isnull=True), name="one_current_price_per_offering"),
            models.CheckConstraint(condition=Q(price_type__in=["FIXED", "FROM", "RANGE", "ON_REQUEST"]), name="price_type_valid"),
            models.CheckConstraint(condition=Q(currency="MXN"), name="price_currency_mxn"),
            models.CheckConstraint(condition=Q(amount_min__gte=0) | Q(amount_min__isnull=True), name="price_min_nonnegative"),
            models.CheckConstraint(condition=Q(amount_max__gte=0) | Q(amount_max__isnull=True), name="price_max_nonnegative"),
            models.CheckConstraint(condition=Q(amount_max__gte=models.F("amount_min")) | Q(amount_max__isnull=True) | Q(amount_min__isnull=True), name="price_range_valid"),
            models.CheckConstraint(
                condition=(
                    Q(price_type="ON_REQUEST", amount_min__isnull=True, amount_max__isnull=True)
                    | Q(price_type__in=["FIXED", "FROM"], amount_min__isnull=False)
                    | Q(price_type="RANGE", amount_min__isnull=False, amount_max__isnull=False)
                ),
                name="price_amounts_match_type",
            ),
            models.CheckConstraint(condition=Q(effective_to__gt=models.F("effective_from")) | Q(effective_to__isnull=True), name="price_period_valid"),
        ]
        indexes = [models.Index(fields=["offering", "-effective_from"])]


class AvailabilityRecord(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponible"
        TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE", "No disponible temporalmente"
        RESERVED = "RESERVED", "Reservada"
        SOLD = "SOLD", "Vendida"

    offering = models.ForeignKey(PropertyOffering, on_delete=models.PROTECT, related_name="availability_history")
    status = models.CharField(max_length=30, choices=Status.choices)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["offering"], condition=Q(effective_to__isnull=True), name="one_current_availability_per_offering"),
            models.CheckConstraint(condition=Q(status__in=["AVAILABLE", "TEMPORARILY_UNAVAILABLE", "RESERVED", "SOLD"]), name="availability_status_valid"),
            models.CheckConstraint(condition=Q(effective_to__gt=models.F("effective_from")) | Q(effective_to__isnull=True), name="availability_period_valid"),
        ]
        indexes = [models.Index(fields=["offering", "-effective_from"])]


class Listing(BusinessModel):
    offering = models.OneToOneField(PropertyOffering, on_delete=models.PROTECT, related_name="listing")
    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=260, unique=True, db_index=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    unpublished_at = models.DateTimeField(null=True, blank=True)
    seo_title = models.CharField(max_length=70, null=True, blank=True)
    seo_description = models.CharField(max_length=170, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["is_published", "archived_at"]), models.Index(fields=["published_at"])]
        permissions = [
            ("publish_listing", "Puede publicar propiedades"),
            ("unpublish_listing", "Puede despublicar propiedades"),
            ("archive_listing", "Puede archivar propiedades"),
            ("restore_listing", "Puede restaurar propiedades"),
            ("hard_delete_listing", "Puede eliminar propiedades definitivamente"),
        ]

    def __str__(self):
        return self.title


class ListingMedia(models.Model):
    class Role(models.TextChoices):
        HERO = "HERO", "Portada"
        GALLERY = "GALLERY", "Galería"
        FLOORPLAN = "FLOORPLAN", "Plano"
        DOCUMENT = "DOCUMENT", "Documento"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="media_links")
    media = models.ForeignKey(MediaAsset, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices)
    sort_order = models.PositiveIntegerField(default=0)


class SlugRedirect(UUIDTimeStampedModel):
    old_path = models.CharField(max_length=500, unique=True)
    new_path = models.CharField(max_length=500)
