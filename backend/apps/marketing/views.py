from rest_framework import serializers, viewsets
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
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

class CampaignViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "analytics.view_bi"
    queryset = MarketingCampaign.objects.all()
    serializer_class = CampaignSerializer
    search_fields = ["name", "utm_campaign", "channel"]

class SpendViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "analytics.view_bi"
    queryset = MarketingSpend.objects.select_related("campaign")
    serializer_class = SpendSerializer
