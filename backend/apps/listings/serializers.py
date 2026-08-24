from rest_framework import serializers
from apps.catalog.models import OfferingAmenity
from .models import AvailabilityRecord, Listing, PriceRecord


def media_url(asset):
    if not asset:
        return None
    try:
        return asset.url
    except Exception:
        return None


class PriceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceRecord
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "effective_to"]

    def validate(self, attrs):
        price_type = attrs.get("price_type", getattr(self.instance, "price_type", None))
        amount_min = attrs.get("amount_min", getattr(self.instance, "amount_min", None))
        amount_max = attrs.get("amount_max", getattr(self.instance, "amount_max", None))
        errors = {}
        if price_type == PriceRecord.Type.ON_REQUEST and (amount_min is not None or amount_max is not None):
            errors["amount_min"] = "Precio a consultar no admite importes."
        elif price_type != PriceRecord.Type.ON_REQUEST and amount_min is None:
            errors["amount_min"] = "Captura el precio mínimo."
        if price_type == PriceRecord.Type.RANGE and amount_max is None:
            errors["amount_max"] = "Captura el precio máximo."
        if amount_min is not None and amount_max is not None and amount_max < amount_min:
            errors["amount_max"] = "El precio máximo no puede ser menor que el mínimo."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class AvailabilityRecordSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    class Meta:
        model = AvailabilityRecord
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "changed_by", "effective_to"]


class PublicListingFilterSerializer(serializers.Serializer):
    developer = serializers.UUIDField(required=False)
    development = serializers.UUIDField(required=False)
    source_type = serializers.ChoiceField(choices=["DEVELOPER", "PRIVATE"], required=False)
    condition = serializers.ChoiceField(choices=["NEW", "USED"], required=False)
    property_type = serializers.SlugField(required=False, max_length=60)
    state = serializers.CharField(required=False, max_length=100)
    municipality = serializers.CharField(required=False, max_length=120)
    query = serializers.CharField(required=False, max_length=200)
    location = serializers.CharField(required=False, max_length=120)
    price_min = serializers.DecimalField(required=False, min_value=0, max_digits=14, decimal_places=2)
    price_max = serializers.DecimalField(required=False, min_value=0, max_digits=14, decimal_places=2)
    bedrooms_min = serializers.DecimalField(required=False, min_value=0, max_digits=4, decimal_places=1)
    bathrooms_min = serializers.DecimalField(required=False, min_value=0, max_digits=4, decimal_places=1)
    parking_min = serializers.IntegerField(required=False, min_value=0)
    construction_area = serializers.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    land_area = serializers.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    amenities = serializers.CharField(required=False, max_length=2000)
    ordering = serializers.ChoiceField(choices=["newest", "price_asc", "price_desc", "area_desc"], required=False)

    def validate(self, attrs):
        if attrs.get("price_min") is not None and attrs.get("price_max") is not None and attrs["price_max"] < attrs["price_min"]:
            raise serializers.ValidationError({"price_max": "El precio máximo no puede ser menor que el mínimo."})
        if attrs.get("amenities") and len(attrs["amenities"].split(",")) > 50:
            raise serializers.ValidationError({"amenities": "Se enviaron demasiadas amenidades."})
        return attrs


class PublicListingSerializer(serializers.ModelSerializer):
    propertyType = serializers.CharField(source="offering.property_type.code")
    propertyTypeName = serializers.CharField(source="offering.property_type.name")
    sourceType = serializers.CharField(source="offering.source_type")
    condition = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    priceMax = serializers.SerializerMethodField()
    priceLabel = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    municipality = serializers.SerializerMethodField()
    neighborhood = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    bedrooms = serializers.DecimalField(source="offering.bedrooms_min", max_digits=4, decimal_places=1, allow_null=True)
    bathrooms = serializers.DecimalField(source="offering.bathrooms_total", max_digits=4, decimal_places=1, allow_null=True)
    fullBathrooms = serializers.IntegerField(source="offering.full_bathrooms", allow_null=True)
    halfBathrooms = serializers.IntegerField(source="offering.half_bathrooms", allow_null=True)
    parkingSpaces = serializers.IntegerField(source="offering.parking_min", allow_null=True)
    constructionM2 = serializers.SerializerMethodField()
    constructionAreaBasis = serializers.CharField(source="offering.construction_area_basis", allow_null=True)
    landM2 = serializers.SerializerMethodField()
    landAreaBasis = serializers.CharField(source="offering.land_area_basis", allow_null=True)
    gardenM2 = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    amenitySlugs = serializers.SerializerMethodField()
    developerId = serializers.SerializerMethodField()
    developerName = serializers.SerializerMethodField()
    developmentId = serializers.SerializerMethodField()
    developmentName = serializers.SerializerMethodField()
    modelName = serializers.SerializerMethodField()
    heroImage = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    floorplans = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    published = serializers.BooleanField(source="is_published")
    featured = serializers.BooleanField(source="is_featured")
    shortDescription = serializers.CharField(source="short_description")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Listing
        fields = ["id", "slug", "title", "propertyType", "propertyTypeName", "sourceType", "condition", "status", "published", "featured", "price", "priceMax", "currency", "priceLabel", "state", "municipality", "neighborhood", "latitude", "longitude", "bedrooms", "bathrooms", "fullBathrooms", "halfBathrooms", "parkingSpaces", "constructionM2", "constructionAreaBasis", "landM2", "landAreaBasis", "gardenM2", "shortDescription", "description", "amenities", "amenitySlugs", "developerId", "developerName", "developmentId", "developmentName", "modelName", "heroImage", "gallery", "floorplans", "createdAt", "updatedAt"]

    def current_price(self, obj):
        cached = getattr(obj.offering, "prices_cache", None)
        return next((item for item in cached if item.effective_to is None), None) if cached is not None else obj.offering.prices.filter(effective_to__isnull=True).first()
    def get_price(self, obj):
        p = self.current_price(obj); return p.amount_min if p else None
    def get_priceMax(self, obj):
        p = self.current_price(obj); return p.amount_max if p else None
    def get_priceLabel(self, obj):
        p = self.current_price(obj); return p.price_type.lower().replace("on_request", "on-request") if p else None
    def get_currency(self, obj):
        p = self.current_price(obj); return p.currency if p else None
    def get_condition(self, obj): return obj.offering.condition.lower() if obj.offering.condition else None
    def location(self, obj): return obj.offering.effective_location()
    def get_state(self, obj):
        value = self.location(obj)["state"]; return value.name if value else None
    def get_municipality(self, obj):
        value = self.location(obj)["municipality"]; return value.name if value else None
    def get_neighborhood(self, obj):
        value = self.location(obj)["neighborhood"]; return value.name if value else None
    def get_latitude(self, obj): return self.location(obj)["latitude"]
    def get_longitude(self, obj): return self.location(obj)["longitude"]
    def get_constructionM2(self, obj): return obj.offering.construction_area_max or obj.offering.construction_area_min
    def get_landM2(self, obj): return obj.offering.land_area_max or obj.offering.land_area_min
    def get_gardenM2(self, obj): return obj.offering.garden_area_max or obj.offering.garden_area_min
    def get_amenities(self, obj):
        links = getattr(obj.offering, "amenity_links_cache", None)
        if links is not None:
            return [link.amenity.name for link in links]
        return list(OfferingAmenity.objects.filter(offering=obj.offering).values_list("amenity__name", flat=True))
    def get_amenitySlugs(self, obj):
        links = getattr(obj.offering, "amenity_links_cache", None)
        if links is not None:
            return [link.amenity.slug for link in links]
        return list(OfferingAmenity.objects.filter(offering=obj.offering).values_list("amenity__slug", flat=True))
    def link(self, obj): return obj.offering.development_model
    def get_developerId(self, obj): return self.link(obj).development.developer_id if self.link(obj) else None
    def get_developerName(self, obj): return self.link(obj).development.developer.name if self.link(obj) else None
    def get_developmentId(self, obj): return self.link(obj).development_id if self.link(obj) else None
    def get_developmentName(self, obj): return self.link(obj).development.name if self.link(obj) else None
    def get_modelName(self, obj): return self.link(obj).housing_model.name if self.link(obj) else None
    def media(self, obj):
        cached = getattr(obj, "media_cache", None)
        return cached if cached is not None else list(obj.media_links.select_related("media").order_by("sort_order"))
    def get_heroImage(self, obj):
        link = next((x for x in self.media(obj) if x.role == "HERO"), None); return media_url(link.media) if link else None
    def get_gallery(self, obj): return [media_url(x.media) for x in self.media(obj) if x.role in ("HERO", "GALLERY")]
    def get_floorplans(self, obj): return [media_url(x.media) for x in self.media(obj) if x.role == "FLOORPLAN"]
    def get_status(self, obj):
        cached = getattr(obj.offering, "availability_cache", None)
        current = cached[0] if cached else (obj.offering.availability_history.filter(effective_to__isnull=True).first() if cached is None else None)
        return current.status.lower() if current else None


class AdminListingSerializer(serializers.ModelSerializer):
    offering_detail = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    current_availability = serializers.SerializerMethodField()
    public_data = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    class Meta:
        model = Listing
        exclude = ["created_by", "updated_by", "archived_by"]
        read_only_fields = ["id", "created_at", "updated_at", "archived_at", "published_at", "unpublished_at"]
    def get_offering_detail(self, obj):
        from apps.catalog.serializers import OfferingSerializer
        return OfferingSerializer(obj.offering).data
    def get_current_price(self, obj):
        cached = getattr(obj.offering, "prices_cache", None)
        p = cached[0] if cached else (obj.offering.prices.filter(effective_to__isnull=True).first() if cached is None else None)
        return PriceRecordSerializer(p).data if p else None
    def get_current_availability(self, obj):
        cached = getattr(obj.offering, "availability_cache", None)
        a = cached[0] if cached else (obj.offering.availability_history.filter(effective_to__isnull=True).first() if cached is None else None)
        return AvailabilityRecordSerializer(a).data if a else None
    def get_public_data(self, obj):
        return PublicListingSerializer(obj, context=self.context).data
    def get_media(self, obj):
        links = getattr(obj, "media_cache", None)
        if links is None:
            links = obj.media_links.select_related("media").order_by("sort_order")
        return [
            {"media_id": str(link.media_id), "role": link.role, "sort_order": link.sort_order, "url": media_url(link.media)}
            for link in links
        ]
