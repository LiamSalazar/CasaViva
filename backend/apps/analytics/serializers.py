from rest_framework import serializers
from .models import AnalyticsEvent, AnonymousVisitor, WebSession
from .schemas import validate_event


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
        if not WebSession.objects.filter(pk=attrs["session_id"], visitor_id=attrs["visitor_id"]).exists():
            raise serializers.ValidationError({"session_id": "Sesión desconocida."})
        return attrs

    def create(self, validated_data):
        listing = validated_data.get("listing")
        if listing:
            validated_data["listing_public_key"] = listing.pk
            validated_data["listing_title_snapshot"] = listing.title
        return super().create(validated_data)
