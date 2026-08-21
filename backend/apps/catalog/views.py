from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.audit.services import audit_event
from apps.common.exceptions import Conflict
from apps.common.services import archive_entity, require_current_version, restore_entity
from rest_framework.exceptions import ValidationError
from apps.common.exports import csv_response
from .models import Amenity, Developer, Development, DevelopmentModel, FeatureDefinition, HousingModel, PropertyOffering, PropertyType
from .serializers import AmenitySerializer, DeveloperSerializer, DevelopmentSerializer, DevelopmentModelSerializer, FeatureDefinitionSerializer, HousingModelSerializer, OfferingSerializer, PropertyTypeSerializer


class BusinessViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    search_fields = ["name"]

    def get_queryset(self):
        qs = self.queryset
        if self.request.query_params.get("archived") == "all" and hasattr(qs.model, "all_objects"):
            archived = qs.model.all_objects.all()
            return archived.order_by(*qs.query.order_by) if qs.query.order_by else archived.order_by("id")
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        audit_event(self.request.user, "CREATE", obj, request=self.request)

    def perform_update(self, serializer):
        require_current_version(self.request.data.get("version"), serializer.instance.version)
        before = {f.name: str(getattr(serializer.instance, f.name)) for f in serializer.instance._meta.fields}
        obj = serializer.save(updated_by=self.request.user, version=serializer.instance.version + 1)
        audit_event(self.request.user, "UPDATE", obj, old_values=before, request=self.request)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        archive_entity(obj, request.user)
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        obj = self.queryset.model.all_objects.get(pk=pk)
        restore_entity(obj, request.user)
        return Response(self.get_serializer(obj).data)


class DeveloperViewSet(BusinessViewSet):
    required_permission = "catalog.manage_developers"
    queryset = Developer.objects.order_by("name", "id")
    serializer_class = DeveloperSerializer

class DevelopmentViewSet(BusinessViewSet):
    required_permission = "catalog.manage_developments"
    queryset = Development.objects.select_related("developer", "state", "municipality", "locality", "neighborhood").prefetch_related("developmentamenity_set__amenity", "media_links__media").order_by("name", "id")
    serializer_class = DevelopmentSerializer
    filterset_fields = ["developer", "state", "municipality", "is_active", "is_published"]

    def perform_update(self, serializer):
        old_slug = serializer.instance.slug
        super().perform_update(serializer)
        if serializer.instance.slug != old_slug:
            from apps.listings.models import SlugRedirect
            SlugRedirect.objects.update_or_create(
                old_path=f"/desarrollos/{old_slug}",
                defaults={"new_path": f"/desarrollos/{serializer.instance.slug}"},
            )

class HousingModelViewSet(BusinessViewSet):
    required_permission = "catalog.manage_models"
    queryset = HousingModel.objects.select_related("developer").order_by("name", "id")
    serializer_class = HousingModelSerializer
    filterset_fields = ["developer", "is_active"]

class DevelopmentModelViewSet(BusinessViewSet):
    required_permission = "catalog.manage_models"
    queryset = DevelopmentModel.objects.select_related("development__developer", "housing_model").order_by("development__name", "housing_model__name", "id")
    serializer_class = DevelopmentModelSerializer
    filterset_fields = ["development", "housing_model", "is_active"]
    search_fields = ["development__name", "housing_model__name"]

class OfferingViewSet(BusinessViewSet):
    required_permission = "catalog.manage_offerings"
    queryset = PropertyOffering.objects.select_related("property_type", "development_model__development__developer", "development_model__housing_model").order_by("-updated_at", "id")
    serializer_class = OfferingSerializer
    filterset_fields = ["source_type", "development_model", "property_type", "state", "municipality", "is_active"]
    search_fields = ["internal_reference", "variant_name", "development_model__development__name", "development_model__housing_model__name"]

    def perform_update(self, serializer):
        if hasattr(serializer.instance, "listing"):
            raise ValidationError("Modifica esta oferta mediante la propiedad completa.")
        super().perform_update(serializer)

    def destroy(self, request, *args, **kwargs):
        if hasattr(self.get_object(), "listing"):
            raise ValidationError("Archiva esta oferta mediante la propiedad completa.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = []
        for item in self.filter_queryset(self.get_queryset()):
            link = item.development_model
            rows.append([
                str(item.id), item.get_source_type_display(), item.property_type.name,
                link.development.developer.name if link else "",
                link.development.name if link else "",
                link.housing_model.name if link else "",
                item.variant_name or "", item.internal_reference or "", item.updated_at.isoformat(),
            ])
        return csv_response("propiedades.csv", ["Identificador", "Origen", "Tipo", "Desarrolladora", "Desarrollo", "Modelo", "Variante", "Referencia", "Actualizado"], rows)

class CatalogViewSet(viewsets.ModelViewSet):
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

class PropertyTypeViewSet(CatalogViewSet):
    queryset = PropertyType.objects.all()
    serializer_class = PropertyTypeSerializer

class AmenityViewSet(CatalogViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer

class FeatureViewSet(CatalogViewSet):
    queryset = FeatureDefinition.objects.order_by("sort_order", "label", "id")
    serializer_class = FeatureDefinitionSerializer
    search_fields = ["label", "code", "category"]
