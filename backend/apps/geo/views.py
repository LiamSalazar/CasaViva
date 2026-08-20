from rest_framework import viewsets

from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.audit.services import audit_event

from .models import Locality, Municipality, Neighborhood, State
from .serializers import LocalityAdminSerializer, MunicipalityAdminSerializer, NeighborhoodAdminSerializer, StateAdminSerializer


class GeoCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "catalog.manage_catalogs"
    search_fields = ["name"]

    def perform_create(self, serializer):
        obj = serializer.save()
        audit_event(self.request.user, "CREATE", obj, request=self.request)

    def perform_update(self, serializer):
        before = {field.name: str(getattr(serializer.instance, field.name)) for field in serializer.instance._meta.fields}
        obj = serializer.save()
        audit_event(self.request.user, "UPDATE", obj, old_values=before, request=self.request)


class StateViewSet(GeoCatalogViewSet):
    queryset = State.objects.all()
    serializer_class = StateAdminSerializer


class MunicipalityViewSet(GeoCatalogViewSet):
    queryset = Municipality.objects.select_related("state")
    serializer_class = MunicipalityAdminSerializer
    filterset_fields = ["state", "is_active", "is_featured"]


class LocalityViewSet(GeoCatalogViewSet):
    queryset = Locality.objects.select_related("municipality")
    serializer_class = LocalityAdminSerializer
    filterset_fields = ["municipality", "is_active"]


class NeighborhoodViewSet(GeoCatalogViewSet):
    queryset = Neighborhood.objects.select_related("municipality", "locality")
    serializer_class = NeighborhoodAdminSerializer
    filterset_fields = ["municipality", "locality", "is_active"]
