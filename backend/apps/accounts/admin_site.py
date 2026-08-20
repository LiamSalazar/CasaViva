from datetime import datetime, timedelta

from django.contrib.admin import AdminSite
from django.utils import timezone

from .models import User


class CasaVivaTechnicalAdminSite(AdminSite):
    site_header = "CasaViva"
    site_title = "CasaViva"
    index_title = "Administración técnica restringida"

    def has_permission(self, request):
        verified_at = request.session.get("mfa_verified_at")
        try:
            mfa_recent = verified_at and timezone.now() - datetime.fromisoformat(verified_at) <= timedelta(hours=8)
        except (TypeError, ValueError):
            mfa_recent = False
        return bool(request.user.is_active and request.user.is_superuser and mfa_recent)


technical_admin_site = CasaVivaTechnicalAdminSite(name="casaviva_technical_admin")
technical_admin_site.register(User)
