import uuid
from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    action = models.CharField(max_length=50, db_index=True)
    entity_type = models.CharField(max_length=120, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    request_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    ip_hash = models.CharField(max_length=64, null=True, blank=True)
    user_agent = models.CharField(max_length=300, null=True, blank=True)
    success = models.BooleanField(default=True)
    reason = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-occurred_at"]
        permissions = [("view_audit", "Puede consultar auditoría"), ("hard_delete_business_record", "Puede eliminar registros de negocio definitivamente")]

    def save(self, *args, **kwargs):
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise RuntimeError("Los eventos de auditoría son inmutables")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Los eventos de auditoría no pueden eliminarse")
