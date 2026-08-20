from django.conf import settings
from django.db import models
from apps.common.models import UUIDTimeStampedModel


class MediaAsset(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        IMAGE = "IMAGE", "Imagen"
        VIDEO = "VIDEO", "Video"
        FLOORPLAN = "FLOORPLAN", "Plano"
        DOCUMENT = "DOCUMENT", "Documento"
        TOUR = "TOUR", "Recorrido"

    storage_key = models.CharField(max_length=500, unique=True)
    media_type = models.CharField(max_length=20, choices=Type.choices)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    byte_size = models.PositiveBigIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, db_index=True)
    alt_text = models.CharField(max_length=300, null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="media_uploads")

    def __str__(self):
        return self.original_filename
