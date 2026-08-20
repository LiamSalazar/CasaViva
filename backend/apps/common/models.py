import uuid
from django.conf import settings
from django.db import models


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)

    def archived(self):
        return self.filter(archived_at__isnull=False)

    def with_archived(self):
        return self.all()


class ActiveManager(models.Manager.from_queryset(ActiveQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(archived_at__isnull=True)


class UUIDTimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BusinessModel(UUIDTimeStampedModel):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="%(app_label)s_%(class)s_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="%(app_label)s_%(class)s_updated")
    version = models.PositiveIntegerField(default=1)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    archived_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="%(app_label)s_%(class)s_archived")

    objects = ActiveManager()
    all_objects = ActiveQuerySet.as_manager()

    class Meta:
        abstract = True


class SourceRecord(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        OFFICIAL_WEBSITE = "OFFICIAL_WEBSITE", "Sitio oficial"
        BROCHURE = "BROCHURE", "Folleto"
        VISIT = "VISIT", "Visita"
        INVENTORY_LIST = "INVENTORY_LIST", "Lista de inventario"
        MANUAL = "MANUAL", "Captura manual"
        OTHER = "OTHER", "Otra"

    source_type = models.CharField(max_length=24, choices=Type.choices)
    source_name = models.CharField(max_length=200)
    source_url = models.URLField(null=True, blank=True)
    observed_at = models.DateTimeField()
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.source_name
