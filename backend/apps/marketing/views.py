from rest_framework import serializers, viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils import timezone
from apps.accounts.permissions import IsMfaVerifiedAdmin
from apps.audit.services import audit_event
from .models import MarketingCampaign, MarketingSpend

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingCampaign
        exclude = ["created_by", "updated_by", "archived_by"]

class SpendSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    class Meta:
        model = MarketingSpend
        fields = "__all__"

class MarketingPermission(BasePermission):
    message = "No tienes permiso para administrar marketing."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if request.method in SAFE_METHODS:
            return user.has_perm("analytics.view_bi") or user.has_perm(view.view_permission) or user.has_perm(view.manage_permission)
        return user.has_perm(view.manage_permission)


class MarketingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, MarketingPermission]

    def perform_create(self, serializer):
        values = {}
        if hasattr(serializer.Meta.model, "created_by"):
            values = {"created_by": self.request.user, "updated_by": self.request.user}
        obj = serializer.save(**values)
        audit_event(self.request.user, "CREATE", obj, request=self.request)

    def perform_update(self, serializer):
        values = {"updated_by": self.request.user} if hasattr(serializer.Meta.model, "updated_by") else {}
        obj = serializer.save(**values)
        audit_event(self.request.user, "UPDATE", obj, request=self.request)

    def perform_destroy(self, instance):
        audit_event(self.request.user, "HARD_DELETE", instance, request=self.request, reason="Corrección de registro de marketing")
        instance.delete()


class CampaignViewSet(MarketingViewSet):
    view_permission = "marketing.view_campaigns"
    manage_permission = "marketing.manage_campaigns"
    queryset = MarketingCampaign.objects.all()
    serializer_class = CampaignSerializer
    search_fields = ["name", "utm_campaign", "channel"]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.archived_at = timezone.now()
        instance.archived_by = self.request.user
        instance.updated_by = self.request.user
        instance.version += 1
        instance.save(update_fields=["is_active", "archived_at", "archived_by", "updated_by", "version", "updated_at"])
        audit_event(self.request.user, "ARCHIVE", instance, request=self.request)

class SpendViewSet(MarketingViewSet):
    view_permission = "marketing.view_spend"
    manage_permission = "marketing.manage_spend"
    queryset = MarketingSpend.objects.select_related("campaign")
    serializer_class = SpendSerializer
