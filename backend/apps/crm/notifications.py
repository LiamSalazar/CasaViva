import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def notify_new_inquiry(inquiry):
    recipient = settings.LEAD_NOTIFICATION_EMAIL
    if not recipient or settings.LEAD_NOTIFICATION_BACKEND != "django_email":
        return
    admin_url = f"{settings.PUBLIC_SITE_URL.rstrip('/')}/administracion/consultas"
    listing = inquiry.listing.title if inquiry.listing_id else "Consulta general"
    body = f"ID: {inquiry.id}\nNombre: {inquiry.lead}\nInmueble: {listing}\nFecha: {inquiry.created_at.isoformat()}\nAdministración: {admin_url}"
    try:
        send_mail(f"Nueva consulta CasaViva · {inquiry.id}", body, None, [recipient], fail_silently=False)
    except Exception:
        logger.exception("No fue posible notificar la nueva consulta", extra={"inquiry_id": str(inquiry.id)})
