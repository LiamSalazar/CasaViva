from rest_framework import serializers
from .models import AnalyticsEvent, AnonymousVisitor, WebSession
from .schemas import validate_event


class StartSessionSerializer(serializers.Serializer):
    visitor_id = serializers.UUIDField(required=False, allow_null=True)
    utm_source = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)
    utm_medium = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)
    utm_campaign = serializers.CharField(max_length=160, required=False, allow_blank=True, allow_null=True)
    utm_content = serializers.CharField(max_length=160, required=False, allow_blank=True, allow_null=True)
    utm_term = serializers.CharField(max_length=160, required=False, allow_blank=True, allow_null=True)
    referrer_domain = serializers.CharField(max_length=250, required=False, allow_blank=True, allow_null=True)
    landing_path = serializers.CharField(max_length=500, required=False, default="/")
    device_category = serializers.ChoiceField(
        choices=["desktop", "tablet", "mobile"], required=False, allow_null=True,
    )
    consent_state = serializers.ChoiceField(
        choices=["ESSENTIAL", "GRANTED", "DENIED"], required=False, default="ESSENTIAL",
    )

    def validate_visitor_id(self, value):
        if value is not None and not AnonymousVisitor.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Visitante desconocido.")
        return value

    def validate(self, attrs):
        # DRF's CharField intentionally coerces a few primitive values.  A
        # public tracking endpoint must reject structured values instead of
        # persisting their string representation.
        for field in (
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
            "referrer_domain", "landing_path", "device_category", "consent_state",
        ):
            if field in self.initial_data and self.initial_data[field] is not None and not isinstance(self.initial_data[field], str):
                raise serializers.ValidationError({field: "Debe ser texto."})
        return attrs


class EventSerializer(serializers.ModelSerializer):
    visitor_id = serializers.UUIDField()
    session_id = serializers.UUIDField()

    class Meta:
        model = AnalyticsEvent
        fields = ["occurred_at", "event_name", "schema_version", "visitor_id", "session_id", "listing", "offering", "development", "page_path", "properties"]

    def validate(self, attrs):
        validate_event(attrs["event_name"], attrs.get("schema_version", 1), attrs.get("properties", {}))
        if not AnonymousVisitor.objects.filter(pk=attrs["visitor_id"]).exists():
            raise serializers.ValidationError({"visitor_id": "Visitante desconocido."})
        session = WebSession.objects.filter(pk=attrs["session_id"], visitor_id=attrs["visitor_id"]).first()
        if session is None:
            raise serializers.ValidationError({"session_id": "Sesión desconocida."})
        supplied_lead = attrs.get("lead")
        if supplied_lead and session.lead_id and supplied_lead.pk != session.lead_id:
            raise serializers.ValidationError({"lead": "El cliente no corresponde a la sesión."})
        attrs["lead"] = session.lead
        return attrs

    def create(self, validated_data):
        listing = validated_data.get("listing")
        if listing:
            validated_data["listing_public_key"] = listing.pk
            validated_data["listing_title_snapshot"] = listing.title
        return super().create(validated_data)


class WebSessionAttributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebSession
        fields = [
            "id", "visitor_id", "lead_id", "started_at", "last_seen_at", "utm_source",
            "utm_medium", "utm_campaign", "utm_content", "utm_term", "referrer_domain",
            "landing_path", "device_category", "consent_state",
        ]
