from rest_framework import serializers
from django.db import transaction
from .models import AboutContent, Guide, HomeContent, HomeHeroSlide, LocationContent, SiteSettings


class HttpUrlField(serializers.URLField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if value and not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Utiliza una dirección http o https válida.")
        return value


class PublicSiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["brand_name", "responsible_name", "operator_type", "commercial_role", "commercial_role_display", "responsible_address", "privacy_email", "contact_email", "complaints_email", "contact_phone", "facebook_url", "instagram_url", "tiktok_url"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {key: value for key, value in data.items() if value and "PENDIENTE" not in str(value).upper()}


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
        fields = ["id", "key", "brand_name", "responsible_name", "operator_type", "commercial_role", "commercial_role_display", "responsible_address", "privacy_email", "contact_email", "complaints_email", "contact_phone", "verification_warning_days", "facebook_url", "instagram_url", "tiktok_url", "version"]
        read_only_fields = ["id", "version"]

    def validate(self, attrs):
        if attrs.get("key", getattr(self.instance, "key", "main")) != "main":
            raise serializers.ValidationError({"key": "CasaViva utiliza una única configuración principal."})
        if self.instance is None and SiteSettings.all_objects.exists():
            raise serializers.ValidationError("La configuración principal ya existe; edítala en lugar de crear otra.")
        return attrs


class AboutContentSerializer(serializers.ModelSerializer):
    hero_media_url = serializers.SerializerMethodField()

    class Meta:
        model = AboutContent
        fields = ["id", "key", "eyebrow", "hero_title", "hero_media", "hero_media_url", "main_title", "main_body", "what_we_do_title", "what_we_do_body", "how_we_work_title", "how_we_work_body", "vision_title", "vision_body", "cta_label", "cta_url", "version", "created_at", "updated_at"]
        read_only_fields = ["id", "hero_media_url", "version", "created_at", "updated_at"]

    def get_hero_media_url(self, obj):
        return obj.hero_media.url if obj.hero_media_id else None

    def validate(self, attrs):
        if attrs.get("key", getattr(self.instance, "key", "main")) != "main":
            raise serializers.ValidationError({"key": "CasaViva utiliza un único contenido de Nosotros."})
        if self.instance is None and AboutContent.all_objects.exists():
            raise serializers.ValidationError("El contenido de Nosotros ya existe; edítalo.")
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
