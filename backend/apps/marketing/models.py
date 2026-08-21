from django.db import models
from apps.common.models import BusinessModel, UUIDTimeStampedModel


class MarketingCampaign(BusinessModel):
    name = models.CharField(max_length=180)
    utm_campaign = models.CharField(max_length=160, unique=True)
    channel = models.CharField(max_length=80)
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
    currency = models.CharField(max_length=3, default="MXN")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=0), name="marketing_spend_nonnegative")]
        permissions = [
            ("view_spend", "Puede consultar gasto de marketing"),
            ("manage_spend", "Puede administrar gasto de marketing"),
        ]
