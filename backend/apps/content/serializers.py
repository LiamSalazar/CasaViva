from rest_framework import serializers
from .models import Guide, HomeContent, LocationContent

class GuideSerializer(serializers.ModelSerializer):
    heroImage = serializers.SerializerMethodField()
    published = serializers.BooleanField(source="is_published")
    featured = serializers.BooleanField(source="is_featured")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    class Meta:
        model = Guide
        fields = ["id", "slug", "title", "excerpt", "content", "category", "heroImage", "published", "featured", "createdAt", "version"]
        read_only_fields = ["id", "heroImage", "createdAt", "version"]
    def get_heroImage(self, obj): return f"/media/{obj.hero_media.storage_key}" if obj.hero_media_id else None

class HomeContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeContent
        fields = ["id", "key", "hero_eyebrow", "hero_title", "editorial_title", "editorial_body", "version"]
        read_only_fields = ["id", "version"]


class LocationContentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="municipality.name", read_only=True)
    state = serializers.CharField(source="municipality.state.name", read_only=True)
    state_id = serializers.UUIDField(source="municipality.state_id", read_only=True)
    heroImage = serializers.SerializerMethodField()

    class Meta:
        model = LocationContent
        fields = ["id", "municipality", "name", "state", "state_id", "slug", "description", "hero_media", "heroImage", "is_featured", "latitude", "longitude", "version", "archived_at"]
        read_only_fields = ["id", "name", "state", "state_id", "heroImage", "version", "archived_at"]

    def get_heroImage(self, obj):
        return f"/media/{obj.hero_media.storage_key}" if obj.hero_media_id else None
