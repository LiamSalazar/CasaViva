from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Guide, HomeContent, LocationContent
from .serializers import GuideSerializer, HomeContentSerializer, LocationContentSerializer
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.audit.services import audit_event
from apps.common.exceptions import Conflict
from apps.common.services import archive_entity, restore_entity
from rest_framework.decorators import action
from rest_framework.response import Response

class PublicGuideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Guide.objects.filter(is_published=True).order_by("-created_at", "id")
    serializer_class = GuideSerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

class ContentBusinessViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "content.manage_content"

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        audit_event(self.request.user, "CREATE", obj, request=self.request)

    def perform_update(self, serializer):
        if int(self.request.data.get("version", -1)) != serializer.instance.version:
            raise Conflict()
        obj = serializer.save(updated_by=self.request.user, version=serializer.instance.version + 1)
        audit_event(self.request.user, "UPDATE", obj, request=self.request)

    def destroy(self, request, *args, **kwargs):
        archive_entity(self.get_object(), request.user)
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        obj = self.queryset.model.all_objects.get(pk=pk)
        restore_entity(obj, request.user)
        return Response(self.get_serializer(obj).data)


class GuideViewSet(ContentBusinessViewSet):
    queryset = Guide.objects.order_by("-updated_at", "id")
    serializer_class = GuideSerializer
    search_fields = ["title", "category"]

    def perform_update(self, serializer):
        old_slug = serializer.instance.slug
        super().perform_update(serializer)
        if serializer.instance.slug != old_slug:
            from apps.listings.models import SlugRedirect
            SlugRedirect.objects.update_or_create(
                old_path=f"/guias/{old_slug}",
                defaults={"new_path": f"/guias/{serializer.instance.slug}"},
            )

class HomeContentViewSet(ContentBusinessViewSet):
    queryset = HomeContent.objects.all()
    serializer_class = HomeContentSerializer


class LocationContentViewSet(ContentBusinessViewSet):
    queryset = LocationContent.objects.select_related("municipality__state", "hero_media").order_by("municipality__name", "id")
    serializer_class = LocationContentSerializer
    search_fields = ["municipality__name", "municipality__state__name", "slug"]

    def get_queryset(self):
        if self.request.query_params.get("archived") == "all":
            return LocationContent.all_objects.select_related("municipality__state", "hero_media").order_by("municipality__name", "id")
        return self.queryset
