import os
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.content.models import SiteSettings
from apps.crm.legal_services import find_unresolved_legal_placeholders
from apps.crm.models import PrivacyNoticeVersion, TermsOfUseVersion


class Command(BaseCommand):
    help = "Valida requisitos críticos sin modificar servicios ni recursos AWS."

    def handle(self, *args, **options):
        failures: list[str] = []
        warnings: list[str] = []

        def require(condition, message):
            if not condition:
                failures.append(message)

        require(not settings.DEBUG, "DEBUG debe estar desactivado")
        require(bool(settings.SECRET_KEY) and settings.SECRET_KEY != "unsafe-development-only" and len(settings.SECRET_KEY) >= 32, "DJANGO_SECRET_KEY es inseguro")
        require(bool(settings.ALLOWED_HOSTS) and "*" not in settings.ALLOWED_HOSTS, "ALLOWED_HOSTS debe ser explícito")
        require(bool(settings.CSRF_TRUSTED_ORIGINS), "CSRF_TRUSTED_ORIGINS debe ser explícito")
        require(getattr(settings, "SESSION_COOKIE_SECURE", False), "SESSION_COOKIE_SECURE debe estar activo")
        require(getattr(settings, "CSRF_COOKIE_SECURE", False), "CSRF_COOKIE_SECURE debe estar activo")
        require(getattr(settings, "SECURE_SSL_REDIRECT", False), "HTTPS redirect no está configurado")
        require(bool(os.environ.get("PUBLIC_DOMAIN")), "falta PUBLIC_DOMAIN")
        require(bool(os.environ.get("ACME_EMAIL")), "falta ACME_EMAIL para Caddy")
        require(settings.STORAGE_BACKEND == "s3", "STORAGE_BACKEND debe ser s3")
        require(bool(os.environ.get("S3_BUCKET_NAME")), "falta el bucket privado de media")
        require(bool(os.environ.get("MEDIA_REMOTE_HOSTNAME")), "falta MEDIA_REMOTE_HOSTNAME")
        require(not os.environ.get("AWS_ACCESS_KEY_ID") and not os.environ.get("AWS_SECRET_ACCESS_KEY"), "no se permiten credenciales AWS estáticas")

        app_url = os.environ.get("APP_DATABASE_URL", os.environ.get("DATABASE_URL", ""))
        require(urlsplit(app_url).username == "casaviva_app", "APP_DATABASE_URL debe usar casaviva_app")
        require(urlsplit(os.environ.get("MIGRATOR_DATABASE_URL", "")).username == "casaviva_migrator", "MIGRATOR_DATABASE_URL debe usar casaviva_migrator")
        require(urlsplit(os.environ.get("BACKUP_DATABASE_URL", "")).username == "casaviva_backup", "BACKUP_DATABASE_URL debe usar casaviva_backup")
        require(os.environ.get("BACKUP_S3_URI", "").startswith("s3://"), "falta BACKUP_S3_URI")

        site = SiteSettings.objects.filter(key="main").first()
        if not site:
            failures.append("falta la identidad pública")
        else:
            required = {"brand_name": site.brand_name, "responsible_name": site.responsible_name, "responsible_address": site.responsible_address, "privacy_email": site.privacy_email, "contact_phone": site.contact_phone}
            failures.extend(f"falta {name}" for name, value in required.items() if not value.strip())
            require(bool(site.contact_email or site.complaints_email), "falta contact_email o complaints_email")
            require(site.operator_type == "PERSONA_FISICA", "operator_type no corresponde al modelo legal vigente")
            require(site.commercial_role == "EXTERNAL_PROMOTER", "commercial_role debe ser EXTERNAL_PROMOTER")

        for model, label in ((PrivacyNoticeVersion, "Aviso de Privacidad"), (TermsOfUseVersion, "Términos de Uso")):
            document = model.objects.filter(status="PUBLISHED", is_active=True, production_ready=True).first()
            if not document:
                failures.append(f"falta una versión production-ready publicada de {label}")
            elif not document.title.strip() or not document.body.strip() or not document.content_hash or not document.effective_at or not document.published_at:
                failures.append(f"{label} no tiene título, contenido, hash o fechas requeridas")
            elif find_unresolved_legal_placeholders(document.body):
                failures.append(f"{label} contiene placeholders")

        if connection.vendor == "postgresql":
            connection.ensure_connection()
            require(connection.connection.info.user == "casaviva_app", "la aplicación no usa el rol casaviva_app")
        require(TOTPDevice.objects.filter(confirmed=True, user__is_active=True, user__is_staff=True).exists(), "MFA administrativo no está inicializado")

        if settings.ANTIBOT_ENABLED:
            require(settings.ANTIBOT_PROVIDER == "turnstile", "ANTIBOT_PROVIDER debe ser turnstile")
            require(bool(settings.TURNSTILE_SECRET_KEY), "falta TURNSTILE_SECRET_KEY")
            require(bool(os.environ.get("NEXT_PUBLIC_TURNSTILE_SITE_KEY")), "falta NEXT_PUBLIC_TURNSTILE_SITE_KEY")
        if settings.LEAD_NOTIFICATION_BACKEND not in {"disabled", "console"}:
            require(bool(settings.LEAD_NOTIFICATION_EMAIL), "falta LEAD_NOTIFICATION_EMAIL")
            require(bool(os.environ.get("DEFAULT_FROM_EMAIL")), "falta DEFAULT_FROM_EMAIL")
        if not getattr(settings, "SECURE_HSTS_SECONDS", 0):
            warnings.append("SECURE_HSTS_SECONDS es 0; habilitar después de confirmar HTTPS estable")

        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"WARN {warning}"))
        if failures:
            for failure in failures:
                self.stderr.write(self.style.ERROR(f"FAIL {failure}"))
            raise CommandError(f"FAIL: {len(failures)} requisito(s) crítico(s) pendiente(s)")
        self.stdout.write(self.style.SUCCESS("PASS CasaViva cumple los checks críticos de producción."))
