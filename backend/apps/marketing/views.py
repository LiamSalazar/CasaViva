from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils import timezone
from apps.accounts.permissions import IsMfaVerifiedAdmin
from apps.accounts.security import has_recent_mfa
from apps.audit.services import audit_event
from .models import MarketingCampaign, MarketingSpend
from apps.analytics.models import WebSession
from apps.crm.models import Inquiry, Sale, Visit

class CampaignSerializer(serializers.ModelSerializer):
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)
    actual_spend = serializers.SerializerMethodField()
    available_budget = serializers.SerializerMethodField()
    execution_percent = serializers.SerializerMethodField()

    class Meta:
        model = MarketingCampaign
        exclude = ["created_by", "updated_by", "archived_by"]

    def get_actual_spend(self, obj):
        return obj.spend.filter(is_voided=False).aggregate(total=Sum("amount"))["total"] or 0

    def get_available_budget(self, obj):
        return obj.planned_budget - self.get_actual_spend(obj)

    def get_execution_percent(self, obj):
        return round(self.get_actual_spend(obj) / obj.planned_budget * 100, 2) if obj.planned_budget else None

    def validate(self, attrs):
        if attrs.get("planned_budget", getattr(self.instance, "planned_budget", 0)) < 0:
            raise serializers.ValidationError({"planned_budget": "El presupuesto no puede ser negativo."})
        path = attrs.get("default_landing_path", getattr(self.instance, "default_landing_path", "/"))
        if not path.startswith("/") or path.startswith("//"):
            raise serializers.ValidationError({"default_landing_path": "Usa una ruta pública que comience con /."})
        return attrs

class SpendSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    class Meta:
        model = MarketingSpend
        fields = [
            "id", "campaign", "campaign_name", "date", "amount", "currency",
            "is_voided", "voided_at", "voided_by", "void_reason", "created_at", "updated_at",
        ]
        read_only_fields = ["is_voided", "voided_at", "voided_by", "void_reason"]

    def validate(self, attrs):
        if self.instance and self.instance.is_voided:
            raise serializers.ValidationError("Este gasto fue anulado y ya no puede modificarse.")
        return attrs

class VoidSpendSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=500)

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
    queryset = MarketingCampaign.objects.order_by("-start_date", "name", "id")
    serializer_class = CampaignSerializer
    search_fields = ["name", "utm_campaign", "channel"]

    def get_queryset(self):
        if self.request.query_params.get("archived") == "all":
            return MarketingCampaign.all_objects.order_by("-start_date", "name", "id")
        return self.queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.archived_at = timezone.now()
        instance.archived_by = self.request.user
        instance.updated_by = self.request.user
        instance.version += 1
        instance.save(update_fields=["is_active", "archived_at", "archived_by", "updated_by", "version", "updated_at"])
        audit_event(self.request.user, "ARCHIVE", instance, request=self.request)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        campaign = MarketingCampaign.all_objects.get(pk=pk)
        campaign.archived_at = None
        campaign.archived_by = None
        campaign.is_active = True
        campaign.updated_by = request.user
        campaign.version += 1
        campaign.save(update_fields=["archived_at", "archived_by", "is_active", "updated_by", "version", "updated_at"])
        audit_event(request.user, "RESTORE", campaign, request=request)
        return Response(self.get_serializer(campaign).data)

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        campaign = self.get_object()
        sessions = WebSession.objects.filter(utm_campaign=campaign.utm_campaign)
        lead_ids = list(sessions.exclude(lead__isnull=True).values_list("lead_id", flat=True).distinct())
        inquiries = Inquiry.objects.filter(lead_id__in=lead_ids).count()
        visits = Visit.objects.filter(lead_id__in=lead_ids, status=Visit.Status.COMPLETED).count()
        sales = Sale.objects.filter(lead_id__in=lead_ids, status=Sale.Status.CLOSED)
        totals = sales.aggregate(value=Sum("sale_price"), commission=Sum("commission_amount"))
        spend = campaign.spend.filter(is_voided=False).aggregate(total=Sum("amount"))["total"] or 0
        commission = totals["commission"] or 0
        count = sales.count()
        ratio = lambda denominator: spend / denominator if spend and denominator else None
        return Response({
            "planned_budget": campaign.planned_budget, "spend": spend,
            "available_budget": campaign.planned_budget - spend,
            "execution_percent": round(spend / campaign.planned_budget * 100, 2) if campaign.planned_budget else None,
            "sessions": sessions.count(), "acquired_clients": len(lead_ids), "inquiries": inquiries,
            "completed_visits": visits, "closed_sales": count,
            "attributed_sales_value": totals["value"] or 0, "attributed_commission": commission,
            "cost_per_client": ratio(len(lead_ids)), "cost_per_inquiry": ratio(inquiries),
            "cost_per_visit": ratio(visits), "cost_per_sale": ratio(count),
            "contribution_after_advertising": commission - spend,
            "return_on_ad_spend": commission / spend if spend else None,
            "public_site_url": settings.PUBLIC_SITE_URL.rstrip("/"),
        })

class SpendViewSet(MarketingViewSet):
    view_permission = "marketing.view_spend"
    manage_permission = "marketing.manage_spend"
    queryset = MarketingSpend.objects.select_related("campaign").order_by("-date", "id")
    serializer_class = SpendSerializer

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "El gasto conserva su historial. Utiliza la acción Anular."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def void(self, request, pk=None):
        if not has_recent_mfa(request):
            return Response({"detail": "Confirma nuevamente tu MFA para anular este gasto."}, status=403)
        serializer = VoidSpendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        spend = MarketingSpend.objects.select_for_update().get(pk=self.get_object().pk)
        if spend.is_voided:
            return Response(self.get_serializer(spend).data)
        spend.is_voided = True
        spend.voided_at = timezone.now()
        spend.voided_by = request.user
        spend.void_reason = serializer.validated_data["reason"]
        spend.save(update_fields=["is_voided", "voided_at", "voided_by", "void_reason", "updated_at"])
        audit_event(request.user, "VOID", spend, request=request, reason=spend.void_reason)
        return Response(self.get_serializer(spend).data)
