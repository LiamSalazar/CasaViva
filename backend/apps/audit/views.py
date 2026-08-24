from rest_framework import serializers, viewsets
from apps.accounts.permissions import CanViewAudit, IsMfaVerifiedAdmin
from .models import AuditEvent

class AuditSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor_user.full_name", read_only=True)
    action_label = serializers.SerializerMethodField()
    class Meta:
        model = AuditEvent
        exclude = ["ip_hash", "user_agent"]
    def get_action_label(self, obj): return obj.action.replace("_", " ").title()

class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, CanViewAudit]
    queryset = AuditEvent.objects.select_related("actor_user").order_by("-occurred_at", "id")
    serializer_class = AuditSerializer
    filterset_fields = ["actor_user", "action", "entity_type", "success"]
    search_fields = ["entity_type", "entity_id", "reason"]
