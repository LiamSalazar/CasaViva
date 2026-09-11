from django.conf import settings
from django.db import models
from django.db.models import Q
import hashlib
from apps.common.models import BusinessModel, UUIDTimeStampedModel
from apps.catalog.models import PropertyOffering
from apps.listings.models import Listing


class Lead(BusinessModel):
    class Status(models.TextChoices):
        NEW = "NEW", "Nuevo"
        CONTACTED = "CONTACTED", "Contactado"
        INTERESTED = "INTERESTED", "Interesado"
        VISIT_SCHEDULED = "VISIT_SCHEDULED", "Visita programada"
        NEGOTIATING = "NEGOTIATING", "Negociación"
        WON = "WON", "Ganado"
        LOST = "LOST", "Perdido"

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(null=True, blank=True, db_index=True)
    phone_raw = models.CharField(max_length=50, null=True, blank=True)
    phone_normalized = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.NEW, db_index=True)
    owner_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_leads")
    first_source = models.CharField(max_length=100, null=True, blank=True)
    last_source = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "owner_user"]), models.Index(fields=["-created_at"])]
        permissions = [("manage_leads", "Puede administrar clientes")]

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip() if self.email else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()


class LeadStageHistory(UUIDTimeStampedModel):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="stage_history")
    stage = models.CharField(max_length=25, choices=Lead.Status.choices)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lead"], condition=Q(ended_at__isnull=True), name="one_current_lead_stage")]


class Inquiry(UUIDTimeStampedModel):
    class Intent(models.TextChoices):
        INFORMATION = "INFORMATION", "Solicitud de información"
        VISIT_REQUEST = "VISIT_REQUEST", "Solicitud de visita"
        GENERAL_CONTACT = "GENERAL_CONTACT", "Contacto general"
    class Subject(models.TextChoices):
        PROPERTY_INFORMATION = "PROPERTY_INFORMATION", "Información de una propiedad"
        SEARCH_ASSISTANCE = "SEARCH_ASSISTANCE", "Ayuda con mi búsqueda"
        GENERAL_COMMENT = "GENERAL_COMMENT", "Comentario general"
    class Channel(models.TextChoices):
        WEB = "WEB", "Sitio web"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        PHONE = "PHONE", "Teléfono"
        EMAIL = "EMAIL", "Correo"
        SOCIAL = "SOCIAL", "Red social"
        MANUAL = "MANUAL", "Captura manual"
    class Status(models.TextChoices):
        NEW = "NEW", "Nueva"
        VIEWED = "VIEWED", "Vista"
        ATTENDED = "ATTENDED", "Atendida"

    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="inquiries")
    listing = models.ForeignKey(Listing, null=True, blank=True, on_delete=models.SET_NULL, related_name="inquiries")
    channel = models.CharField(max_length=15, choices=Channel.choices)
    intent = models.CharField(max_length=20, choices=Intent.choices, default=Intent.INFORMATION, db_index=True)
    subject = models.CharField(max_length=30, choices=Subject.choices, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    session_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.NEW)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_inquiries")

    class Meta:
        permissions = [("manage_inquiries", "Puede administrar consultas")]


class LeadInterest(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        VIEWED = "VIEWED", "Vista"
        FAVORITED = "FAVORITED", "Favorita"
        INQUIRED = "INQUIRED", "Consultada"
        VISITED = "VISITED", "Visitada"
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="interests")
    offering = models.ForeignKey(PropertyOffering, on_delete=models.PROTECT, related_name="lead_interests")
    interest_type = models.CharField(max_length=15, choices=Type.choices)


class Visit(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Programada"
        COMPLETED = "COMPLETED", "Realizada"
        CANCELLED = "CANCELLED", "Cancelada"
        NO_SHOW = "NO_SHOW", "No asistió"
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="visits")
    offering = models.ForeignKey(PropertyOffering, on_delete=models.PROTECT, related_name="visits")
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    completed_at = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_visits")
    notes = models.TextField(null=True, blank=True)

    class Meta:
        permissions = [("manage_visits", "Puede administrar visitas")]


class Sale(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        CLOSED = "CLOSED", "Cerrada"
        CANCELLED = "CANCELLED", "Cancelada"
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="sales")
    offering = models.ForeignKey(PropertyOffering, on_delete=models.PROTECT, related_name="sales")
    listing = models.ForeignKey(Listing, null=True, blank=True, on_delete=models.PROTECT, related_name="sales")
    sale_price = models.DecimalField(max_digits=14, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    closed_at = models.DateTimeField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.CLOSED)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_sales")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(sale_price__gte=0), name="sale_price_nonnegative"),
            models.CheckConstraint(condition=Q(status__in=["CLOSED", "CANCELLED"]), name="sale_status_valid"),
        ]
        permissions = [("manage_sales", "Puede administrar ventas")]


class LegalDocumentVersionBase(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PUBLISHED = "PUBLISHED", "Publicada"
        RETIRED = "RETIRED", "Retirada"

    version = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=250, blank=True)
    body = models.TextField(blank=True)
    effective_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    content_hash = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=False)
    historical_content_available = models.BooleanField(default=True)
    production_ready = models.BooleanField(
        default=False,
        help_text="Revisión explícita contra el modelo legal vigente; las versiones legacy no satisfacen readiness.",
    )

    class Meta:
        abstract = True

    @staticmethod
    def normalize_content(value):
        return "\n".join(line.rstrip() for line in (value or "").replace("\r\n", "\n").replace("\r", "\n").strip().split("\n"))

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.status in (self.Status.PUBLISHED, self.Status.RETIRED):
                protected = ("version", "title", "body", "effective_at", "published_at", "published_by_id", "content_hash")
                if any(getattr(previous, name) != getattr(self, name) for name in protected):
                    raise ValueError("Una versión legal publicada es inmutable.")
        if self.body:
            self.content_hash = hashlib.sha256(self.normalize_content(self.body).encode("utf-8")).hexdigest()
        super().save(*args, **kwargs)


class PrivacyNoticeVersion(LegalDocumentVersionBase):
    class Meta:
        permissions = [("publish_privacy_notice", "Puede publicar avisos de privacidad")]
        constraints = [models.UniqueConstraint(fields=["is_active"], condition=Q(is_active=True), name="one_active_privacy_notice")]


class TermsOfUseVersion(LegalDocumentVersionBase):
    class Meta:
        permissions = [("publish_terms_of_use", "Puede publicar términos de uso")]
        constraints = [models.UniqueConstraint(fields=["is_active"], condition=Q(is_active=True), name="one_active_terms_of_use")]


class ConsentRecord(UUIDTimeStampedModel):
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.PROTECT, related_name="consents")
    visitor_id = models.UUIDField(null=True, blank=True)
    privacy_notice_version = models.ForeignKey(PrivacyNoticeVersion, on_delete=models.PROTECT)
    purpose = models.CharField(max_length=100)
    granted = models.BooleanField()
    granted_at = models.DateTimeField()
    source = models.CharField(max_length=100)
