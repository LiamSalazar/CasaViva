from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.audit.services import audit_event


@transaction.atomic
def archive_entity(entity, actor, reason=None):
    if entity.archived_at:
        return entity
    entity.archived_at = timezone.now()
    entity.archived_by = actor
    if hasattr(entity, "updated_by"):
        entity.updated_by = actor
    entity.version += 1
    entity.save()
    audit_event(actor, "ARCHIVE", entity, reason=reason)
    return entity


@transaction.atomic
def restore_entity(entity, actor, reason=None):
    entity.archived_at = None
    entity.archived_by = None
    if hasattr(entity, "updated_by"):
        entity.updated_by = actor
    entity.version += 1
    entity.save()
    audit_event(actor, "RESTORE", entity, reason=reason)
    return entity


def assert_version(entity, expected):
    if expected is None or int(expected) != entity.version:
        raise ValidationError({"version": "Este registro fue modificado mientras lo estabas editando. Actualiza la información antes de guardar tus cambios."}, code="conflict")
