from django.db import transaction
from django.db.models.deletion import ProtectedError
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action

from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.audit.services import audit_event
from apps.accounts.security import has_recent_mfa
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

    def dependency_summary(self, obj):
        dependencies = {}
        for relation in obj._meta.related_objects:
            accessor = relation.get_accessor_name()
            try:
                related = getattr(obj, accessor)
                count = 1 if relation.one_to_one else related.count()
            except relation.related_model.DoesNotExist:
                count = 0
            if count:
                dependencies[relation.related_model._meta.verbose_name_plural] = count
        return dependencies

    @action(detail=True, methods=["get"], url_path="delete-preview")
    def delete_preview(self, request, pk=None):
        obj = self.get_object()
        dependencies = self.dependency_summary(obj)
        return Response({
            "dependencies": dependencies,
            "can_delete": not obj.is_active and not dependencies,
            "confirmation": obj.name,
        })

    @action(detail=True, methods=["post"], url_path="hard-delete")
    @transaction.atomic
    def hard_delete(self, request, pk=None):
        if not has_recent_mfa(request):
            return Response({"detail": "Vuelve a verificar tu identidad para continuar."}, status=403)
        confirmation = request.data.get("confirmation")
        reason = request.data.get("reason")
        if confirmation != self.get_object().name:
            raise serializers.ValidationError({"confirmation": "Escribe exactamente el nombre de la ubicación."})
        if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 500:
            raise serializers.ValidationError({"reason": "Explica el motivo en 10 a 500 caracteres."})
        obj = self.queryset.model.objects.select_for_update().get(pk=pk)
        dependencies = self.dependency_summary(obj)
        if obj.is_active:
            raise serializers.ValidationError({"detail": "Desactiva la ubicación antes de eliminarla definitivamente."})
        if dependencies:
            raise serializers.ValidationError({"detail": "Esta ubicación está en uso y sólo puede mantenerse inactiva.", "dependencies": dependencies})
        audit_event(
            request.user, "HARD_DELETE", obj,
            old_values={field.name: str(getattr(obj, field.name)) for field in obj._meta.fields},
            request=request, reason=reason.strip(),
        )
        try:
            obj.delete()
        except ProtectedError:
            raise serializers.ValidationError({"detail": "Esta ubicación está en uso y sólo puede mantenerse inactiva."})
        return Response(status=status.HTTP_204_NO_CONTENT)


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
