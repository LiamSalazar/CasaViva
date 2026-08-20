from rest_framework import serializers

from .models import Locality, Municipality, Neighborhood, State


class StateAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = "__all__"


class MunicipalityAdminSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = Municipality
        fields = "__all__"


class LocalityAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Locality
        fields = "__all__"


class NeighborhoodAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Neighborhood
        fields = "__all__"
