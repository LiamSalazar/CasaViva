from rest_framework import viewsets

from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.audit.services import audit_event
from rest_framework.response import Response

from .models import Locality, Municipality, Neighborhood, State
from .serializers import LocalityAdminSerializer, MunicipalityAdminSerializer, NeighborhoodAdminSerializer, StateAdminSerializer


class GeoCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "catalog.manage_catalogs"
    search_fields = ["name"]
    filterset_fields = ["is_active"]

    def perform_create(self, serializer):
        obj = serializer.save()
        audit_event(self.request.user, "CREATE", obj, request=self.request)

    def perform_update(self, serializer):
        before = {field.name: str(getattr(serializer.instance, field.name)) for field in serializer.instance._meta.fields}
        obj = serializer.save()
        audit_event(self.request.user, "UPDATE", obj, old_values=before, request=self.request)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        old = obj.is_active
        obj.is_active = False
        obj.save(update_fields=["is_active", "updated_at"])
        audit_event(request.user, "UPDATE", obj, old_values={"is_active": old}, new_values={"is_active": False}, request=request)
        return Response(status=204)


class StateViewSet(GeoCatalogViewSet):
    queryset = State.objects.order_by("name", "id")
    serializer_class = StateAdminSerializer


class MunicipalityViewSet(GeoCatalogViewSet):
    queryset = Municipality.objects.select_related("state").order_by("state__name", "name", "id")
    serializer_class = MunicipalityAdminSerializer
    filterset_fields = ["state", "is_active", "is_featured"]


class LocalityViewSet(GeoCatalogViewSet):
    queryset = Locality.objects.select_related("municipality").order_by("name", "id")
    serializer_class = LocalityAdminSerializer
    filterset_fields = ["municipality", "is_active"]


class NeighborhoodViewSet(GeoCatalogViewSet):
    queryset = Neighborhood.objects.select_related("municipality", "locality").order_by("name", "id")
    serializer_class = NeighborhoodAdminSerializer
    filterset_fields = ["municipality", "locality", "is_active"]
