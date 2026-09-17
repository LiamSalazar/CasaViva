from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.security import has_recent_mfa
from apps.audit.services import audit_event


LEGAL_PLACEHOLDERS = (
    "[DOMICILIO DEL RESPONSABLE]",
    "[CORREO DE PRIVACIDAD]",
    "[CORREO DE CONTACTO O QUEJAS]",
    "[TELÉFONO DE CONTACTO]",
)


def find_unresolved_legal_placeholders(body):
    normalized = (body or "").upper()
    return [placeholder for placeholder in LEGAL_PLACEHOLDERS if placeholder in normalized]


@transaction.atomic
def publish_legal_version(document, actor, request, permission):
    if not (actor.is_superuser or actor.has_perm(permission)):
        raise PermissionDenied("No tienes permiso para publicar este documento.")
    if not has_recent_mfa(request):
        raise PermissionDenied("Confirma nuevamente MFA para publicar contenido legal.")
    document = type(document).objects.select_for_update().get(pk=document.pk)
    if document.status != document.Status.DRAFT:
        raise ValidationError({"status": "Sólo puede publicarse un borrador."})
    if not document.production_ready:
        raise ValidationError({"production_ready": "Marca el documento como revisado y apto para producción antes de publicarlo."})
    if not document.title.strip() or not document.body.strip() or find_unresolved_legal_placeholders(document.body):
        raise ValidationError({"body": "Completa el documento y elimina todos los placeholders antes de publicarlo."})
    now = timezone.now()
    type(document).objects.filter(is_active=True).update(status=document.Status.RETIRED, is_active=False)
    document.status = document.Status.PUBLISHED
    document.is_active = True
    document.published_at = now
    document.effective_at = document.effective_at or now
    document.published_by = actor
    document.save()
    audit_event(actor, "LEGAL_DOCUMENT_PUBLISHED", document, request=request, new_values={"version": document.version, "content_hash": document.content_hash})
    return document
