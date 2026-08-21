from rest_framework import serializers
from .models import Inquiry, Lead, PrivacyNoticeVersion, Sale, Visit
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
    visitor_id = serializers.UUIDField(required=False, allow_null=True)
    privacy_consent = serializers.BooleanField()
    privacy_notice_version = serializers.PrimaryKeyRelatedField(queryset=PrivacyNoticeVersion.objects.filter(is_active=True), required=False)

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Captura correo o teléfono.")
        if not attrs["privacy_consent"]:
            raise serializers.ValidationError({"privacy_consent": "Debes aceptar el aviso de privacidad."})
        notice = attrs.get("privacy_notice_version") or PrivacyNoticeVersion.objects.filter(is_active=True).order_by("-published_at").first()
        if not notice:
            raise serializers.ValidationError({"privacy_consent": "El aviso de privacidad no está disponible temporalmente."})
        attrs["privacy_notice_version"] = notice
        if attrs.get("session_id") and not attrs.get("visitor_id"):
            raise serializers.ValidationError({"visitor_id": "Incluye el visitante asociado a la sesión."})
        if attrs.get("visitor_id") and not attrs.get("session_id"):
            raise serializers.ValidationError({"session_id": "Incluye la sesión de navegación."})
        return attrs

    def create(self, data):
        slug = data.pop("listing_slug", None)
        data.pop("privacy_consent", None)
        listing = Listing.objects.filter(slug=slug, is_published=True).first() if slug else None
        if slug and listing is None:
            raise serializers.ValidationError({"listing_slug": "La propiedad indicada no está disponible."})
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

    def validate(self, attrs):
        if attrs.get("sale_price") is not None and attrs["sale_price"] < 0:
            raise serializers.ValidationError({"sale_price": "El precio de venta no puede ser negativo."})
        rate = attrs.get("commission_rate")
        if rate is not None and not 0 <= rate <= 100:
            raise serializers.ValidationError({"commission_rate": "La comisión debe estar entre 0 y 100%."})
        listing = attrs.get("listing")
        offering = attrs.get("offering")
        if listing and offering and listing.offering_id != offering.id:
            raise serializers.ValidationError({"listing": "La publicación no corresponde a la propiedad seleccionada."})
        return attrs
