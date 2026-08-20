from django.db import models
from apps.common.models import UUIDTimeStampedModel
from apps.catalog.models import Development, PropertyOffering
from apps.crm.models import Lead
from apps.listings.models import Listing


class AnonymousVisitor(UUIDTimeStampedModel):
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()


class WebSession(UUIDTimeStampedModel):
    visitor = models.ForeignKey(AnonymousVisitor, on_delete=models.PROTECT, related_name="sessions")
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name="web_sessions")
    started_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    utm_source = models.CharField(max_length=120, null=True, blank=True, db_index=True)
    utm_medium = models.CharField(max_length=120, null=True, blank=True)
    utm_campaign = models.CharField(max_length=160, null=True, blank=True, db_index=True)
    utm_content = models.CharField(max_length=160, null=True, blank=True)
    utm_term = models.CharField(max_length=160, null=True, blank=True)
    referrer_domain = models.CharField(max_length=250, null=True, blank=True)
    landing_path = models.CharField(max_length=500)
    device_category = models.CharField(max_length=30, null=True, blank=True)
    consent_state = models.CharField(max_length=30)

    class Meta:
        indexes = [models.Index(fields=["visitor", "started_at"])]


class AnalyticsEvent(UUIDTimeStampedModel):
    occurred_at = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    event_name = models.CharField(max_length=80, db_index=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    visitor = models.ForeignKey(AnonymousVisitor, on_delete=models.PROTECT, related_name="events")
    session = models.ForeignKey(WebSession, on_delete=models.PROTECT, related_name="events")
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events")
    listing = models.ForeignKey(Listing, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events")
    offering = models.ForeignKey(PropertyOffering, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events")
    development = models.ForeignKey(Development, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events")
    page_path = models.CharField(max_length=500, null=True, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    listing_public_key = models.UUIDField(null=True, blank=True)
    listing_title_snapshot = models.CharField(max_length=240, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_name", "-occurred_at"]),
            models.Index(fields=["session", "occurred_at"]),
            models.Index(fields=["listing", "occurred_at"]),
            models.Index(fields=["offering", "occurred_at"]),
        ]
        permissions = [("view_bi", "Puede consultar información de negocio")]
