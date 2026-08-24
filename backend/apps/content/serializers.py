from rest_framework import serializers
from django.db import transaction
from .models import Guide, HomeContent, HomeHeroSlide, LocationContent, SiteSettings


class HttpUrlField(serializers.URLField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if value and not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Utiliza una dirección http o https válida.")
        return value


class PublicSiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["contact_email", "facebook_url", "instagram_url", "tiktok_url"]


class PublicGuideSerializer(serializers.ModelSerializer):
    heroImage = serializers.SerializerMethodField()
    published = serializers.BooleanField(source="is_published", read_only=True)
    featured = serializers.BooleanField(source="is_featured", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Guide
        fields = ["id", "slug", "title", "excerpt", "content", "category", "heroImage", "published", "featured", "createdAt"]

    def get_heroImage(self, obj):
        return obj.hero_media.url if obj.hero_media_id else None


class SiteSettingsSerializer(serializers.ModelSerializer):
    facebook_url = HttpUrlField(required=False, allow_null=True, allow_blank=True)
    instagram_url = HttpUrlField(required=False, allow_null=True, allow_blank=True)
    tiktok_url = HttpUrlField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = SiteSettings
        fields = ["id", "key", "contact_email", "facebook_url", "instagram_url", "tiktok_url", "version"]
        read_only_fields = ["id", "version"]

    def validate(self, attrs):
        if attrs.get("key", getattr(self.instance, "key", "main")) != "main":
            raise serializers.ValidationError({"key": "CasaViva utiliza una única configuración principal."})
        if self.instance is None and SiteSettings.all_objects.exists():
            raise serializers.ValidationError("La configuración principal ya existe; edítala en lugar de crear otra.")
        return attrs


class HomeHeroSlideSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_slug = serializers.CharField(source="listing.slug", read_only=True)

    class Meta:
        model = HomeHeroSlide
        fields = ["id", "listing", "listing_title", "listing_slug", "eyebrow_override", "title_override", "subtitle_override", "sort_order", "is_active", "version"]
        read_only_fields = ["id", "listing_title", "listing_slug", "version"]

class GuideSerializer(serializers.ModelSerializer):
    heroImage = serializers.SerializerMethodField()
    published = serializers.BooleanField(source="is_published")
    featured = serializers.BooleanField(source="is_featured")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    class Meta:
        model = Guide
        fields = ["id", "slug", "title", "excerpt", "content", "category", "hero_media", "heroImage", "published", "featured", "createdAt", "version"]
        read_only_fields = ["id", "heroImage", "createdAt", "version"]
    def get_heroImage(self, obj): return obj.hero_media.url if obj.hero_media_id else None

class HomeContentSerializer(serializers.ModelSerializer):
    hero_slides = HomeHeroSlideSerializer(many=True, required=False)
    editorial_media_url = serializers.SerializerMethodField()

    class Meta:
        model = HomeContent
        fields = ["id", "key", "hero_eyebrow", "hero_title", "editorial_title", "editorial_body", "editorial_media", "editorial_media_url", "hero_slides", "version"]
        read_only_fields = ["id", "editorial_media_url", "version"]

    def get_editorial_media_url(self, obj):
        return obj.editorial_media.url if obj.editorial_media_id else None

    def _save_slides(self, home, slides):
        keep = []
        for values in slides:
            slide, _ = HomeHeroSlide.all_objects.update_or_create(
                home_content=home, listing=values.pop("listing"),
                defaults={**values, "archived_at": None},
            )
            keep.append(slide.pk)
        HomeHeroSlide.objects.filter(home_content=home).exclude(pk__in=keep).update(is_active=False)

    @transaction.atomic
    def create(self, validated_data):
        slides = validated_data.pop("hero_slides", [])
        home = super().create(validated_data)
        self._save_slides(home, slides)
        return home

    @transaction.atomic
    def update(self, instance, validated_data):
        slides = validated_data.pop("hero_slides", None)
        home = super().update(instance, validated_data)
        if slides is not None:
            self._save_slides(home, slides)
        return home


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
        return obj.hero_media.url if obj.hero_media_id else None
