from rest_framework import serializers
from .models import Inquiry, Lead, Sale, Visit
from .services import create_inquiry
from apps.listings.models import Listing


class PublicInquirySerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    message = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    listing_slug = serializers.SlugField(required=False, allow_blank=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    privacy_consent = serializers.BooleanField()

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Captura correo o teléfono.")
        if not attrs["privacy_consent"]:
            raise serializers.ValidationError({"privacy_consent": "Debes aceptar el aviso de privacidad."})
        return attrs

    def create(self, data):
        slug = data.pop("listing_slug", None)
        data.pop("privacy_consent", None)
        listing = Listing.objects.filter(slug=slug, is_published=True).first() if slug else None
        return create_inquiry(listing=listing, **data)


class LeadSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    class Meta:
        model = Lead
        exclude = ["created_by", "updated_by", "archived_by"]
    def get_name(self, obj): return str(obj)


class InquirySerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.__str__", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True, allow_null=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    class Meta:
        model = Inquiry
        fields = "__all__"


class VisitSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.__str__", read_only=True)
    class Meta:
        model = Visit
        fields = "__all__"


class SaleSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.__str__", read_only=True)
    class Meta:
        model = Sale
        fields = "__all__"
        read_only_fields = ["commission_amount", "created_by"]
