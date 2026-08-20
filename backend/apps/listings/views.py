from django.db.models import OuterRef, Subquery, DecimalField, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.catalog.models import Development, PropertyOffering
from apps.geo.models import Municipality
from apps.catalog.serializers import DevelopmentSerializer
from apps.common.exceptions import Conflict
from apps.common.services import archive_entity, restore_entity
from apps.audit.services import audit_event
from .models import Listing, ListingMedia, PriceRecord, AvailabilityRecord, SlugRedirect
from apps.media_library.models import MediaAsset
from drf_spectacular.utils import extend_schema, OpenApiTypes
from .serializers import AdminListingSerializer, AvailabilityRecordSerializer, PriceRecordSerializer, PublicListingSerializer
from .services import change_availability, change_price, hard_delete_listing, publish_listing, unpublish_listing


def public_listing_queryset():
    current_price = PriceRecord.objects.filter(offering=OuterRef("offering_id"), effective_to__isnull=True)
    return Listing.objects.filter(is_published=True, offering__archived_at__isnull=True).select_related(
        "offering__property_type", "offering__state", "offering__municipality",
        "offering__development_model__development__developer", "offering__development_model__development__state",
        "offering__development_model__development__municipality", "offering__development_model__housing_model",
    ).prefetch_related("media_links__media", "offering__availability_history").annotate(current_amount=Subquery(current_price.values("amount_min")[:1], output_field=DecimalField()))


class SearchThrottle(ScopedRateThrottle): scope = "search"

class PublicListingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicListingSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    throttle_classes = [SearchThrottle]

    def get_queryset(self):
        qs = public_listing_queryset()
        p = self.request.query_params
        mappings = {"developer": "offering__development_model__development__developer_id", "development": "offering__development_model__development_id", "source_type": "offering__source_type"}
        for key, field in mappings.items():
            if p.get(key): qs = qs.filter(**{field: p[key]})
        if p.get("state"):
            qs = qs.filter(Q(offering__state__name__iexact=p["state"]) | Q(offering__development_model__development__state__name__iexact=p["state"]))
        if p.get("municipality"):
            qs = qs.filter(Q(offering__municipality__name__iexact=p["municipality"]) | Q(offering__development_model__development__municipality__name__iexact=p["municipality"]))
        if p.get("property_type"):
            qs = qs.filter(offering__property_type__code=p["property_type"])
        if p.get("query"):
            qs = qs.filter(Q(title__icontains=p["query"]) | Q(offering__development_model__development__name__icontains=p["query"]) | Q(offering__development_model__housing_model__name__icontains=p["query"]))
        if p.get("location"):
            qs = qs.filter(Q(offering__municipality__name__icontains=p["location"]) | Q(offering__development_model__development__municipality__name__icontains=p["location"]))
        if p.get("price_min"): qs = qs.filter(current_amount__gte=p["price_min"])
        if p.get("price_max"): qs = qs.filter(current_amount__lte=p["price_max"])
        if p.get("bedrooms_min"): qs = qs.filter(offering__bedrooms_min__gte=p["bedrooms_min"])
        if p.get("bathrooms_min"): qs = qs.filter(offering__bathrooms_total__gte=p["bathrooms_min"])
        if p.get("construction_area"): qs = qs.filter(Q(offering__construction_area_max__gte=p["construction_area"]) | Q(offering__construction_area_min__gte=p["construction_area"]))
        if p.get("land_area"): qs = qs.filter(Q(offering__land_area_max__gte=p["land_area"]) | Q(offering__land_area_min__gte=p["land_area"]))
        if p.get("amenities"): qs = qs.filter(offering__amenity_links__amenity__name__in=p["amenities"].split(",")).distinct()
        ordering = {"newest": "-published_at", "price_asc": "current_amount", "price_desc": "-current_amount", "area_desc": "-offering__construction_area_max"}.get(p.get("ordering"), "-published_at")
        return qs.order_by(ordering)


class ListingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "catalog.manage_offerings"
    serializer_class = AdminListingSerializer
    queryset = Listing.objects.select_related("offering__property_type", "offering__development_model__development__developer", "offering__development_model__housing_model")
    search_fields = ["title", "slug", "offering__internal_reference"]
    filterset_fields = ["is_published", "is_featured", "offering__source_type", "offering__property_type"]

    def get_queryset(self):
        return Listing.all_objects.all() if self.request.query_params.get("archived") == "all" else self.queryset
    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        audit_event(self.request.user, "CREATE", obj, request=self.request)
    def perform_update(self, serializer):
        if int(self.request.data.get("version", -1)) != serializer.instance.version: raise Conflict()
        obj = serializer.save(updated_by=self.request.user, version=serializer.instance.version + 1)
        audit_event(self.request.user, "UPDATE", obj, request=self.request)
    def destroy(self, request, *args, **kwargs):
        listing = self.get_object()
        if listing.is_published: unpublish_listing(listing, request.user, request=request)
        archive_entity(Listing.all_objects.get(pk=listing.pk), request.user)
        return Response(status=204)
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        obj = publish_listing(self.get_object(), request.user, request=request); return Response(self.get_serializer(obj).data)
    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        obj = unpublish_listing(self.get_object(), request.user, request=request); return Response(self.get_serializer(obj).data)
    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        obj = Listing.all_objects.get(pk=pk); restore_entity(obj, request.user); return Response(self.get_serializer(obj).data)
    @action(detail=True, methods=["post"])
    def price(self, request, pk=None):
        listing = self.get_object(); record = change_price(listing.offering, request.user, request=request, **{k: request.data.get(k) for k in ["price_type", "amount_min", "amount_max", "effective_from", "observations"]}); return Response(PriceRecordSerializer(record).data, status=201)
    @action(detail=True, methods=["get"])
    def price_history(self, request, pk=None):
        return Response(PriceRecordSerializer(self.get_object().offering.prices.order_by("-effective_from"), many=True).data)
    @action(detail=True, methods=["post"])
    def availability(self, request, pk=None):
        record = change_availability(self.get_object().offering, request.user, status=request.data["status"], notes=request.data.get("notes"), request=request); return Response(AvailabilityRecordSerializer(record).data, status=201)
    @action(detail=True, methods=["get"])
    def availability_history(self, request, pk=None):
        return Response(AvailabilityRecordSerializer(self.get_object().offering.availability_history.order_by("-effective_from"), many=True).data)
    @action(detail=True, methods=["post"], url_path="media")
    def attach_media(self, request, pk=None):
        listing = self.get_object()
        asset = get_object_or_404(MediaAsset, pk=request.data.get("media_id"))
        role = request.data.get("role", "GALLERY")
        if role not in ListingMedia.Role.values: return Response({"detail": "Rol de multimedia inválido."}, status=400)
        if role == "HERO": ListingMedia.objects.filter(listing=listing, role="HERO").delete()
        link = ListingMedia.objects.create(listing=listing, media=asset, role=role, sort_order=request.data.get("sort_order", 0))
        return Response({"id": link.id}, status=201)
    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        listing = Listing.all_objects.filter(pk=pk).first()
        if not listing: return Response(status=404)
        verified_at = request.session.get("mfa_verified_at")
        if not verified_at or timezone.now() - __import__("datetime").datetime.fromisoformat(verified_at) > __import__("datetime").timedelta(minutes=15):
            return Response({"detail": "Vuelve a verificar tu identidad para continuar."}, status=403)
        hard_delete_listing(listing, request.user, confirmation=request.data.get("confirmation", ""), reason=request.data.get("reason", ""), request=request)
        return Response(status=204)

    @action(detail=True, methods=["get"], url_path="delete-preview")
    def delete_preview(self, request, pk=None):
        from apps.analytics.models import AnalyticsEvent
        from apps.crm.models import Inquiry, Sale

        listing = Listing.all_objects.filter(pk=pk).first()
        if not listing:
            return Response(status=404)
        sales = Sale.objects.filter(Q(listing=listing) | Q(offering=listing.offering)).count()
        return Response({
            "inquiries": Inquiry.objects.filter(listing=listing).count(),
            "analytics_events": AnalyticsEvent.objects.filter(listing=listing).count(),
            "sales": sales,
            "can_delete": listing.archived_at is not None and sales == 0,
        })


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([AllowAny])
def public_home(request):
    from apps.content.models import HomeContent
    from apps.content.serializers import HomeContentSerializer
    listings = public_listing_queryset()
    featured = listings.filter(is_featured=True)[:8]
    if not featured: featured = listings[:8]
    developments = Development.objects.filter(is_published=True).select_related("developer", "state", "municipality")[:8]
    locations = [{"id": item.id, "name": item.name, "state": item.state.name} for item in Municipality.objects.filter(is_active=True, is_featured=True).select_related("state")[:12]]
    content = HomeContent.objects.filter(key="main").first()
    return Response({"hero": PublicListingSerializer(featured[:5], many=True, context={"request": request}).data, "featured_listings": PublicListingSerializer(featured, many=True, context={"request": request}).data, "featured_developments": DevelopmentSerializer(developments, many=True).data, "featured_locations": locations, "content": HomeContentSerializer(content).data if content else None})


@api_view(["GET"])
@permission_classes([AllowAny])
def slug_redirect(request, path):
    redirect = get_object_or_404(SlugRedirect, old_path=f"/{path}")
    return Response({"redirect": redirect.new_path}, status=301)
