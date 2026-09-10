import json
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.analytics.models import WebSession
from apps.crm.models import Lead


class Command(BaseCommand):
    help = "Reporta candidatos según configuración; nunca elimina información."
    def handle(self, *args, **options):
        now = timezone.now()
        analytics_days = settings.ANALYTICS_RETENTION_DAYS
        lead_days = settings.INACTIVE_LEAD_RETENTION_DAYS
        report = {"dry_run": True, "configured": {"analytics_sessions_days": analytics_days, "inactive_leads_days": lead_days}, "candidates": {"sessions": [], "leads": []}}
        if analytics_days: report["candidates"]["sessions"] = [str(x) for x in WebSession.objects.filter(last_seen_at__lt=now-timedelta(days=analytics_days)).values_list("id", flat=True)]
        if lead_days: report["candidates"]["leads"] = [str(x) for x in Lead.objects.filter(updated_at__lt=now-timedelta(days=lead_days)).exclude(status__in=["WON", "NEGOTIATING"]).values_list("id", flat=True)]
        self.stdout.write(json.dumps(report, indent=2))
