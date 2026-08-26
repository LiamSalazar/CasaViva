from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import BusinessModel, UUIDTimeStampedModel


class MarketingCampaign(BusinessModel):
    class Channel(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", "Instagram"
        FACEBOOK = "FACEBOOK", "Facebook"
        TIKTOK = "TIKTOK", "TikTok"
        GOOGLE = "GOOGLE", "Google"
        OTHER = "OTHER", "Otro"

    name = models.CharField(max_length=180)
    utm_campaign = models.CharField(max_length=160, unique=True)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    planned_budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    utm_source = models.CharField(max_length=120)
    utm_medium = models.CharField(max_length=120)
    default_landing_path = models.CharField(max_length=500, default="/")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        permissions = [
            ("view_campaigns", "Puede consultar campañas"),
            ("manage_campaigns", "Puede administrar campañas"),
        ]


class MarketingSpend(UUIDTimeStampedModel):
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.PROTECT, related_name="spend")
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=[("MXN", "MXN")], default="MXN")
    is_voided = models.BooleanField(default=False, db_index=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="voided_marketing_spend")
    void_reason = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="marketing_spend_nonnegative"),
            models.CheckConstraint(condition=Q(currency="MXN"), name="marketing_spend_currency_mxn"),
            models.CheckConstraint(
                condition=Q(is_voided=False, voided_at__isnull=True, voided_by__isnull=True, void_reason__isnull=True)
                | Q(is_voided=True, voided_at__isnull=False, voided_by__isnull=False, void_reason__isnull=False),
                name="marketing_spend_void_consistent",
            ),
        ]
        permissions = [
            ("view_spend", "Puede consultar gasto de marketing"),
            ("manage_spend", "Puede administrar gasto de marketing"),
        ]
