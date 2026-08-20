from rest_framework import serializers
from apps.geo.models import State, Municipality, Locality, Neighborhood
from .models import Amenity, Developer, Development, DevelopmentModel, FeatureChoice, FeatureDefinition, HousingModel, OfferingFeatureValue, PropertyOffering, PropertyType


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
    class Meta:
        model = Development
        exclude = ["created_by", "updated_by", "archived_by"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "archived_at"]

    def validate(self, attrs):
        state = attrs.get("state", getattr(self.instance, "state", None))
        municipality = attrs.get("municipality", getattr(self.instance, "municipality", None))
        if state and municipality and municipality.state_id != state.id:
            raise serializers.ValidationError({"municipality": "El municipio no pertenece al estado seleccionado."})
        developer = attrs.get("developer", getattr(self.instance, "developer", None))
        if self.instance and developer and developer.id != self.instance.developer_id:
            incompatible = self.instance.model_links.filter(archived_at__isnull=True).exclude(housing_model__developer=developer)
            if incompatible.exists():
                names = list(incompatible.values_list("housing_model__name", flat=True)[:10])
                raise serializers.ValidationError({"developer": f"Antes desvincula o reasigna estos modelos: {', '.join(names)}."})
        return attrs


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
    feature_values_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
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
        return attrs

    def get_feature_values(self, obj):
        return [{"definition": str(value.definition_id), "label": value.definition.label, "data_type": value.definition.data_type, "value_boolean": value.value_boolean, "value_number": value.value_number, "value_text": value.value_text, "value_choice": str(value.value_choice_id) if value.value_choice_id else None} for value in obj.feature_values.select_related("definition", "value_choice")]

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

    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        features = validated_data.pop("feature_values_input", [])
        obj = super().create(validated_data)
        obj.amenities.set(amenities)
        self.sync_features(obj, features)
        return obj

    def update(self, instance, validated_data):
        amenities = validated_data.pop("amenities", None)
        features = validated_data.pop("feature_values_input", None)
        obj = super().update(instance, validated_data)
        if amenities is not None:
            obj.amenities.set(amenities)
        self.sync_features(obj, features)
        return obj
