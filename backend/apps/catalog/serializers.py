from rest_framework import serializers
from django.db import transaction
from apps.geo.models import State, Municipality, Locality, Neighborhood
from apps.media_library.models import MediaAsset
from .models import Amenity, Developer, Development, DevelopmentMedia, DevelopmentModel, FeatureChoice, FeatureDefinition, HousingModel, OfferingFeatureValue, PropertyOffering, PropertyType


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "code"]


class MunicipalitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True)
    class Meta:
        model = Municipality
        fields = ["id", "state", "state_name", "name"]


class DeveloperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        exclude = ["created_by", "updated_by", "archived_by"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "archived_at"]


class DevelopmentSerializer(serializers.ModelSerializer):
    developer_name = serializers.CharField(source="developer.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    municipality_name = serializers.CharField(source="municipality.name", read_only=True)
    locality_name = serializers.CharField(source="locality.name", read_only=True, allow_null=True)
    neighborhood_name = serializers.CharField(source="neighborhood.name", read_only=True, allow_null=True)
    amenities = serializers.SerializerMethodField()
    amenity_ids = serializers.PrimaryKeyRelatedField(source="amenities", queryset=Amenity.objects.filter(is_active=True), many=True, required=False)
    media = serializers.SerializerMethodField()
    media_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    class Meta:
        model = Development
        exclude = ["created_by", "updated_by", "archived_by"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "archived_at"]

    def validate(self, attrs):
        state = attrs.get("state", getattr(self.instance, "state", None))
        municipality = attrs.get("municipality", getattr(self.instance, "municipality", None))
        locality = attrs.get("locality", getattr(self.instance, "locality", None))
        neighborhood = attrs.get("neighborhood", getattr(self.instance, "neighborhood", None))
        if state and municipality and municipality.state_id != state.id:
            raise serializers.ValidationError({"municipality": "El municipio no pertenece al estado seleccionado."})
        if locality and municipality and locality.municipality_id != municipality.id:
            raise serializers.ValidationError({"locality": "La localidad no pertenece al municipio seleccionado."})
        if neighborhood and municipality and neighborhood.municipality_id != municipality.id:
            raise serializers.ValidationError({"neighborhood": "La colonia no pertenece al municipio seleccionado."})
        developer = attrs.get("developer", getattr(self.instance, "developer", None))
        if self.instance and developer and developer.id != self.instance.developer_id:
            incompatible = self.instance.model_links.filter(archived_at__isnull=True).exclude(housing_model__developer=developer)
            if incompatible.exists():
                names = list(incompatible.values_list("housing_model__name", flat=True)[:10])
                raise serializers.ValidationError({"developer": f"Antes desvincula o reasigna estos modelos: {', '.join(names)}."})
        return attrs

    def get_amenities(self, obj):
        return [link.amenity.name for link in obj.developmentamenity_set.select_related("amenity").order_by("amenity__sort_order", "amenity__name")]

    def get_media(self, obj):
        return [{"media_id": str(link.media_id), "role": link.role, "sort_order": link.sort_order, "url": f"/media/{link.media.storage_key}"} for link in obj.media_links.select_related("media").order_by("sort_order")]

    def validate_media_input(self, values):
        if sum(item.get("role") == "HERO" for item in values) > 1:
            raise serializers.ValidationError("Sólo puede existir una imagen de portada.")
        valid_roles = set(DevelopmentMedia.Role.values)
        media_ids = [item.get("media_id") for item in values]
        assets = {str(asset.id): asset for asset in MediaAsset.objects.filter(id__in=media_ids)}
        for item in values:
            if item.get("role", "GALLERY") not in valid_roles:
                raise serializers.ValidationError("Rol de multimedia inválido.")
            if str(item.get("media_id")) not in assets:
                raise serializers.ValidationError("Un archivo de multimedia ya no existe.")
        return values

    def _sync_relations(self, obj, amenities, media):
        if amenities is not None:
            obj.amenities.set(amenities)
        if media is not None:
            assets = {str(asset.id): asset for asset in MediaAsset.objects.filter(id__in=[item["media_id"] for item in media])}
            obj.media_links.all().delete()
            DevelopmentMedia.objects.bulk_create([
                DevelopmentMedia(development=obj, media=assets[str(item["media_id"])], role=item.get("role", "GALLERY"), sort_order=item.get("sort_order", 0))
                for item in media
            ])

    @transaction.atomic
    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        media = validated_data.pop("media_input", [])
        obj = super().create(validated_data)
        self._sync_relations(obj, amenities, media)
        return obj

    @transaction.atomic
    def update(self, instance, validated_data):
        amenities = validated_data.pop("amenities", None)
        media = validated_data.pop("media_input", None)
        obj = super().update(instance, validated_data)
        self._sync_relations(obj, amenities, media)
        return obj


class HousingModelSerializer(serializers.ModelSerializer):
    developer_name = serializers.CharField(source="developer.name", read_only=True)
    developments = serializers.SerializerMethodField()
    class Meta:
        model = HousingModel
        exclude = ["created_by", "updated_by", "archived_by"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "archived_at"]

    def get_developments(self, obj):
        return [{"id": str(x.development_id), "link_id": str(x.id), "name": x.development.name} for x in obj.development_links.filter(archived_at__isnull=True).select_related("development")]

    def validate(self, attrs):
        developer = attrs.get("developer", getattr(self.instance, "developer", None))
        if self.instance and developer and developer.id != self.instance.developer_id:
            incompatible = self.instance.development_links.filter(archived_at__isnull=True).exclude(development__developer=developer)
            if incompatible.exists():
                names = list(incompatible.values_list("development__name", flat=True)[:10])
                raise serializers.ValidationError({"developer": f"Antes desvincula el modelo de: {', '.join(names)}."})
        return attrs


class DevelopmentModelSerializer(serializers.ModelSerializer):
    development_name = serializers.CharField(source="development.name", read_only=True)
    model_name = serializers.CharField(source="housing_model.name", read_only=True)
    developer_id = serializers.UUIDField(source="development.developer_id", read_only=True)
    developer_name = serializers.CharField(source="development.developer.name", read_only=True)
    class Meta:
        model = DevelopmentModel
        exclude = ["created_by", "updated_by", "archived_by"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "archived_at"]

    def validate(self, attrs):
        development = attrs.get("development", getattr(self.instance, "development", None))
        model = attrs.get("housing_model", getattr(self.instance, "housing_model", None))
        if development and model and development.developer_id != model.developer_id:
            raise serializers.ValidationError("El desarrollo y el modelo deben pertenecer a la misma desarrolladora.")
        return attrs


class PropertyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = "__all__"


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = "__all__"


class FeatureDefinitionSerializer(serializers.ModelSerializer):
    choices = serializers.SerializerMethodField()

    class Meta:
        model = FeatureDefinition
        fields = "__all__"

    def get_choices(self, obj):
        return [{"id": str(choice.id), "label": choice.label} for choice in obj.choices.order_by("sort_order")]


class OfferingSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source="__str__", read_only=True)
    developer_name = serializers.SerializerMethodField()
    development_name = serializers.SerializerMethodField()
    model_name = serializers.SerializerMethodField()
    amenity_ids = serializers.PrimaryKeyRelatedField(source="amenities", queryset=Amenity.objects.filter(is_active=True), many=True, required=False)
    feature_values = serializers.SerializerMethodField()
    feature_values_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False, max_length=200)
    class Meta:
        model = PropertyOffering
        exclude = ["created_by", "updated_by", "archived_by"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "archived_at"]

    def get_developer_name(self, obj):
        return obj.development_model.development.developer.name if obj.development_model_id else None
    def get_development_name(self, obj):
        return obj.development_model.development.name if obj.development_model_id else None
    def get_model_name(self, obj):
        return obj.development_model.housing_model.name if obj.development_model_id else None

    def validate(self, attrs):
        source = attrs.get("source_type", getattr(self.instance, "source_type", None))
        link = attrs.get("development_model", getattr(self.instance, "development_model", None))
        if (source == "DEVELOPER") != bool(link):
            raise serializers.ValidationError({"development_model": "El origen y la relación seleccionada no son compatibles."})
        state = attrs.get("state", getattr(self.instance, "state", None))
        municipality = attrs.get("municipality", getattr(self.instance, "municipality", None))
        locality = attrs.get("locality", getattr(self.instance, "locality", None))
        neighborhood = attrs.get("neighborhood", getattr(self.instance, "neighborhood", None))
        development = link.development if link else None
        effective_state = state or (development.state if development else None)
        effective_municipality = municipality or (development.municipality if development else None)
        if effective_state and municipality and municipality.state_id != effective_state.id:
            raise serializers.ValidationError({"municipality": "El municipio no pertenece al estado seleccionado."})
        if locality and effective_municipality and locality.municipality_id != effective_municipality.id:
            raise serializers.ValidationError({"locality": "La localidad no pertenece al municipio seleccionado."})
        if neighborhood and effective_municipality and neighborhood.municipality_id != effective_municipality.id:
            raise serializers.ValidationError({"neighborhood": "La colonia no pertenece al municipio seleccionado."})
        return attrs

    def validate_amenity_ids(self, values):
        if len(values) > 200:
            raise serializers.ValidationError("Se enviaron demasiadas amenidades.")
        return values

    def get_feature_values(self, obj):
        values = getattr(obj, "feature_values_cache", None)
        if values is None:
            values = obj.feature_values.select_related("definition", "value_choice")
        return [{"definition": str(value.definition_id), "label": value.definition.label, "data_type": value.definition.data_type, "value_boolean": value.value_boolean, "value_number": value.value_number, "value_text": value.value_text, "value_choice": str(value.value_choice_id) if value.value_choice_id else None} for value in values]

    def sync_features(self, obj, values):
        if values is None:
            return
        definitions = {str(item.id): item for item in FeatureDefinition.objects.filter(id__in=[value.get("definition") for value in values], is_active=True)}
        keep = []
        for payload in values:
            definition = definitions.get(str(payload.get("definition")))
            if not definition:
                raise serializers.ValidationError({"feature_values_input": "Una característica ya no está disponible."})
            fields = {"value_boolean": None, "value_number": None, "value_text": None, "value_choice": None}
            key = {"BOOLEAN": "value_boolean", "NUMBER": "value_number", "TEXT": "value_text", "CHOICE": "value_choice"}[definition.data_type]
            value = payload.get(key)
            if value in (None, ""):
                continue
            if key == "value_choice":
                value = FeatureChoice.objects.filter(pk=value, definition=definition).first()
                if not value:
                    raise serializers.ValidationError({"feature_values_input": "La opción elegida no corresponde a la característica."})
            fields[key] = value
            record, _ = OfferingFeatureValue.objects.update_or_create(offering=obj, definition=definition, defaults=fields)
            record.full_clean()
            keep.append(definition.id)
        obj.feature_values.exclude(definition_id__in=keep).delete()

    @transaction.atomic
    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        features = validated_data.pop("feature_values_input", [])
        obj = super().create(validated_data)
        obj.amenities.set(amenities)
        self.sync_features(obj, features)
        return obj

    @transaction.atomic
    def update(self, instance, validated_data):
        amenities = validated_data.pop("amenities", None)
        features = validated_data.pop("feature_values_input", None)
        obj = super().update(instance, validated_data)
        if amenities is not None:
            obj.amenities.set(amenities)
        self.sync_features(obj, features)
        return obj
