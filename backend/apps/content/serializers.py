from rest_framework import serializers
from .models import Guide, HomeContent

class GuideSerializer(serializers.ModelSerializer):
    heroImage = serializers.SerializerMethodField()
    published = serializers.BooleanField(source="is_published")
    featured = serializers.BooleanField(source="is_featured")
    createdAt = serializers.DateTimeField(source="created_at")
    class Meta:
        model = Guide
        fields = ["id", "slug", "title", "excerpt", "content", "category", "heroImage", "published", "featured", "createdAt", "version"]
    def get_heroImage(self, obj): return f"/media/{obj.hero_media.storage_key}" if obj.hero_media_id else None

class HomeContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeContent
        fields = ["id", "key", "hero_eyebrow", "hero_title", "editorial_title", "editorial_body", "version"]
        read_only_fields = ["id", "version"]
