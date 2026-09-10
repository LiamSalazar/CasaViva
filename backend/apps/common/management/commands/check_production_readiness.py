import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.content.models import SiteSettings
from apps.crm.models import PrivacyNoticeVersion, TermsOfUseVersion


class Command(BaseCommand):
    help = "Valida requisitos críticos sin modificar servicios ni recursos AWS."

    def handle(self, *args, **options):
        errors = []
        if settings.DEBUG: errors.append("DEBUG debe estar desactivado")
        if settings.SECRET_KEY in ("", "unsafe-development-only") or len(settings.SECRET_KEY) < 32: errors.append("DJANGO_SECRET_KEY es inseguro")
        if not settings.ALLOWED_HOSTS or "*" in settings.ALLOWED_HOSTS: errors.append("ALLOWED_HOSTS debe ser explícito")
        if not getattr(settings, "SECURE_SSL_REDIRECT", False): errors.append("HTTPS redirect no está configurado")
        if settings.STORAGE_BACKEND != "s3": errors.append("STORAGE_BACKEND debe ser s3")
        if not os.environ.get("S3_BUCKET_NAME"): errors.append("falta el bucket privado de media")
        site = SiteSettings.objects.filter(key="main").first()
        if not site: errors.append("falta la identidad pública")
        else:
            required = {"responsible_name": site.responsible_name, "responsible_address": site.responsible_address, "privacy_email": site.privacy_email}
            errors.extend(f"falta {name}" for name, value in required.items() if not value.strip())
            if not (site.contact_email or site.complaints_email): errors.append("falta contact_email o complaints_email")
        for model, label in ((PrivacyNoticeVersion, "Aviso de Privacidad"), (TermsOfUseVersion, "Términos de Uso")):
            doc = model.objects.filter(status="PUBLISHED", is_active=True).first()
            if not doc: errors.append(f"falta una versión publicada de {label}")
            elif any(token in doc.body.upper() for token in ("[DOMICILIO", "[CORREO", "[TELÉFONO", "PENDIENTE")): errors.append(f"{label} contiene placeholders")
        if connection.vendor == "postgresql" and connection.settings_dict.get("USER") != "casaviva_app": errors.append("la aplicación no usa el rol casaviva_app")
        if not TOTPDevice.objects.filter(confirmed=True, user__is_active=True, user__is_staff=True).exists(): errors.append("MFA administrativo no está inicializado")
        if errors:
            raise CommandError("Producción no está lista:\n- " + "\n- ".join(errors))
        self.stdout.write(self.style.SUCCESS("CasaViva cumple los checks críticos de producción."))
