from rest_framework import serializers

from apps.catalog.models import PropertyOffering
from apps.catalog.serializers import OfferingSerializer
from apps.media_library.models import MediaAsset
from .models import AvailabilityRecord, Listing, ListingMedia, PriceRecord


class PropertyListingInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            "title", "slug", "short_description", "description", "is_featured",
            "seo_title", "seo_description",
        ]
        extra_kwargs = {"slug": {"validators": []}}


class PropertyPriceInputSerializer(serializers.Serializer):
    price_type = serializers.ChoiceField(choices=PriceRecord.Type.choices)
    amount_min = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    amount_max = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    currency = serializers.ChoiceField(choices=PriceRecord.Currency.choices, default=PriceRecord.Currency.MXN)
    effective_from = serializers.DateTimeField(required=False)
    observations = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        price_type = attrs["price_type"]
        amount_min = attrs.get("amount_min")
        amount_max = attrs.get("amount_max")
        if price_type == PriceRecord.Type.ON_REQUEST:
            if amount_min is not None or amount_max is not None:
                raise serializers.ValidationError({"amount_min": "Precio a consultar no admite importes."})
        elif amount_min is None:
            raise serializers.ValidationError({"amount_min": "Captura el precio mínimo."})
        if price_type == PriceRecord.Type.RANGE and amount_max is None:
            raise serializers.ValidationError({"amount_max": "Captura el precio máximo."})
        if amount_min is not None and amount_max is not None and amount_max < amount_min:
            raise serializers.ValidationError({"amount_max": "El precio máximo no puede ser menor que el mínimo."})
        return attrs


class PropertyAvailabilityInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AvailabilityRecord.Status.choices)
    effective_from = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PropertyMediaInputSerializer(serializers.Serializer):
    media_id = serializers.PrimaryKeyRelatedField(source="media", queryset=MediaAsset.objects.all())
    role = serializers.ChoiceField(choices=ListingMedia.Role.choices, default=ListingMedia.Role.GALLERY)
    sort_order = serializers.IntegerField(min_value=0, default=0)


class PropertyFeaturedInputSerializer(serializers.Serializer):
    is_featured = serializers.BooleanField()
    listing_version = serializers.IntegerField(min_value=1)


class PropertyPublicationInputSerializer(serializers.Serializer):
    is_published = serializers.BooleanField()
    listing_version = serializers.IntegerField(min_value=1)


class PropertyHardDeleteInputSerializer(serializers.Serializer):
    confirmation = serializers.CharField(max_length=300, trim_whitespace=False)
    reason = serializers.CharField(min_length=3, max_length=1000)


class AdminPropertyAggregateInputSerializer(serializers.Serializer):
    offering = serializers.DictField()
    listing = PropertyListingInputSerializer()
    price = PropertyPriceInputSerializer(required=False)
    availability = PropertyAvailabilityInputSerializer(required=False)
    media = PropertyMediaInputSerializer(many=True, required=False, max_length=100)
    published = serializers.BooleanField(required=False, default=False)
    offering_version = serializers.IntegerField(min_value=1, required=False)
    listing_version = serializers.IntegerField(min_value=1, required=False)

    def validate_offering(self, value):
        instance = self.context.get("offering")
        serializer = OfferingSerializer(instance, data=value, partial=instance is not None)
        serializer.is_valid(raise_exception=True)
        self._offering_serializer = serializer
        return value

    def validate(self, attrs):
        is_update = self.context.get("listing") is not None
        if not is_update:
            missing = [name for name in ("price", "availability") if name not in attrs]
            if missing:
                raise serializers.ValidationError({name: "Este campo es obligatorio al crear una propiedad." for name in missing})
        elif "offering_version" not in attrs or "listing_version" not in attrs:
            raise serializers.ValidationError({"version": "Incluye las versiones de la propiedad antes de guardar."})
        media = attrs.get("media")
        if media is not None and sum(item["role"] == ListingMedia.Role.HERO for item in media) > 1:
            raise serializers.ValidationError({"media": "Sólo puede existir una imagen de portada."})
        slug = attrs["listing"]["slug"]
        duplicate = Listing.all_objects.filter(slug=slug)
        if is_update:
            duplicate = duplicate.exclude(pk=self.context["listing"].pk)
        if duplicate.exists():
            raise serializers.ValidationError({"listing": {"slug": "Ya existe una propiedad con esta URL."}})
        return attrs

    @property
    def offering_serializer(self):
        return self._offering_serializer
