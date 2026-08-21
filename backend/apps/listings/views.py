from django.db.models import OuterRef, Subquery, DecimalField, Q, Prefetch, F, Case, When, Value, IntegerField
from django.db.models.functions import Abs, Coalesce
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.accounts.security import has_recent_mfa
from apps.catalog.models import Development, OfferingAmenity, OfferingFeatureValue, PropertyOffering
from apps.geo.models import Municipality
from apps.catalog.serializers import DevelopmentSerializer
from apps.common.exceptions import Conflict
from apps.common.services import archive_entity, restore_entity
from apps.audit.services import audit_event
from .models import Listing, ListingMedia, PriceRecord, AvailabilityRecord, SlugRedirect
from apps.media_library.models import MediaAsset
from drf_spectacular.utils import extend_schema, OpenApiTypes
from .serializers import AdminListingSerializer, AvailabilityRecordSerializer, PriceRecordSerializer, PublicListingFilterSerializer, PublicListingSerializer
from .services import change_availability, change_price, hard_delete_listing, publish_listing, unpublish_listing
from .property_serializers import AdminPropertyAggregateInputSerializer
from .property_services import archive_property, create_property, hard_delete_property, property_dependencies, restore_property, update_property


def public_listing_queryset():
    current_price = PriceRecord.objects.filter(offering=OuterRef("offering_id"), effective_to__isnull=True)
    return Listing.objects.filter(is_published=True, offering__archived_at__isnull=True).select_related(
        "offering__property_type", "offering__state", "offering__municipality",
        "offering__development_model__development__developer", "offering__development_model__development__state",
        "offering__development_model__development__municipality", "offering__development_model__housing_model",
    ).prefetch_related(
        Prefetch("media_links", queryset=ListingMedia.objects.select_related("media").order_by("sort_order"), to_attr="media_cache"),
        Prefetch("offering__prices", queryset=PriceRecord.objects.filter(effective_to__isnull=True), to_attr="prices_cache"),
        Prefetch("offering__availability_history", queryset=AvailabilityRecord.objects.filter(effective_to__isnull=True), to_attr="availability_cache"),
        Prefetch("offering__amenity_links", queryset=OfferingAmenity.objects.select_related("amenity").order_by("amenity__sort_order", "amenity__name"), to_attr="amenity_links_cache"),
    ).annotate(
        current_amount=Subquery(current_price.values("amount_min")[:1], output_field=DecimalField()),
        current_amount_max=Subquery(current_price.values("amount_max")[:1], output_field=DecimalField()),
    )


class SearchThrottle(ScopedRateThrottle): scope = "search"

class PublicListingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicListingSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    throttle_classes = [SearchThrottle]

    def get_queryset(self):
        qs = public_listing_queryset()
        params = PublicListingFilterSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        p = params.validated_data
        mappings = {"developer": "offering__development_model__development__developer_id", "development": "offering__development_model__development_id", "source_type": "offering__source_type", "condition": "offering__condition"}
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
        if p.get("price_min") is not None: qs = qs.filter(Q(current_amount_max__gte=p["price_min"]) | Q(current_amount_max__isnull=True, current_amount__gte=p["price_min"]))
        if p.get("price_max") is not None: qs = qs.filter(current_amount__lte=p["price_max"])
        if p.get("bedrooms_min"): qs = qs.filter(Q(offering__bedrooms_max__gte=p["bedrooms_min"]) | Q(offering__bedrooms_max__isnull=True, offering__bedrooms_min__gte=p["bedrooms_min"]))
        if p.get("bathrooms_min"): qs = qs.filter(offering__bathrooms_total__gte=p["bathrooms_min"])
        if p.get("parking_min"): qs = qs.filter(Q(offering__parking_max__gte=p["parking_min"]) | Q(offering__parking_max__isnull=True, offering__parking_min__gte=p["parking_min"]))
        if p.get("construction_area"): qs = qs.filter(Q(offering__construction_area_max__gte=p["construction_area"]) | Q(offering__construction_area_min__gte=p["construction_area"]))
        if p.get("land_area"): qs = qs.filter(Q(offering__land_area_max__gte=p["land_area"]) | Q(offering__land_area_min__gte=p["land_area"]))
        if p.get("amenities"):
            for amenity in p["amenities"].split(","):
                qs = qs.filter(offering__amenity_links__amenity__name=amenity)
            qs = qs.distinct()
        ordering = p.get("ordering", "newest")
        if ordering == "price_asc":
            return qs.order_by(F("current_amount").asc(nulls_last=True), "-published_at")
        if ordering == "price_desc":
            return qs.order_by(F("current_amount").desc(nulls_last=True), "-published_at")
        if ordering == "area_desc":
            return qs.order_by(F("offering__construction_area_max").desc(nulls_last=True), F("offering__construction_area_min").desc(nulls_last=True))
        return qs.order_by("-published_at")

    @action(detail=False, methods=["get"], url_path="favorites")
    def favorites(self, request):
        from rest_framework.exceptions import ValidationError
        from uuid import UUID

        raw_ids = [value for value in request.query_params.get("ids", "").split(",") if value]
        if len(raw_ids) > 100:
            raise ValidationError({"ids": "Sólo pueden recuperarse 100 favoritos por solicitud."})
        try:
            ids = [UUID(value) for value in raw_ids]
        except ValueError:
            raise ValidationError({"ids": "Uno de los identificadores no es válido."})
        queryset = public_listing_queryset().filter(id__in=ids)
        by_id = {item.id: item for item in queryset}
        ordered = [by_id[item_id] for item_id in ids if item_id in by_id]
        return Response(self.get_serializer(ordered, many=True).data)

    @action(detail=True, methods=["get"], url_path="similar")
    def similar(self, request, slug=None):
        listing = self.get_object()
        location = listing.offering.effective_location()
        price = listing.offering.prices.filter(effective_to__isnull=True).values_list("amount_min", flat=True).first()
        queryset = public_listing_queryset().exclude(pk=listing.pk).annotate(
            location_rank=Case(
                When(Q(offering__municipality_id=getattr(location["municipality"], "id", None)) | Q(offering__development_model__development__municipality_id=getattr(location["municipality"], "id", None)), then=Value(0)),
                default=Value(1), output_field=IntegerField(),
            ),
            type_rank=Case(When(offering__property_type_id=listing.offering.property_type_id, then=Value(0)), default=Value(1), output_field=IntegerField()),
            price_distance=Abs(Coalesce(F("current_amount"), Value(999999999999, output_field=DecimalField())) - Value(price or 0, output_field=DecimalField())),
        ).order_by("location_rank", "type_rank", "price_distance", "-published_at")[:3]
        return Response(self.get_serializer(queryset, many=True).data)


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
        old_slug = serializer.instance.slug
        obj = serializer.save(updated_by=self.request.user, version=serializer.instance.version + 1)
        if obj.slug != old_slug:
            SlugRedirect.objects.update_or_create(
                old_path=f"/propiedades/{old_slug}",
                defaults={"new_path": f"/propiedades/{obj.slug}"},
            )
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
        if not has_recent_mfa(request):
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


class PropertyAggregateViewSet(viewsets.ModelViewSet):
    """Administrative property aggregate used by the complete property form."""

    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "catalog.manage_offerings"
    serializer_class = AdminListingSerializer
    search_fields = ["title", "slug", "offering__internal_reference"]
    filterset_fields = ["is_published", "is_featured", "offering__source_type", "offering__condition", "offering__property_type"]

    def get_queryset(self):
        manager = Listing.all_objects if self.request.query_params.get("archived") == "all" else Listing.objects
        return manager.select_related(
            "offering__property_type", "offering__state", "offering__municipality",
            "offering__locality", "offering__neighborhood",
            "offering__development_model__development__developer",
            "offering__development_model__development__state",
            "offering__development_model__development__municipality",
            "offering__development_model__housing_model",
        ).prefetch_related(
            "offering__amenities",
            Prefetch("offering__amenity_links", queryset=OfferingAmenity.objects.select_related("amenity"), to_attr="amenity_links_cache"),
            Prefetch("offering__feature_values", queryset=OfferingFeatureValue.objects.select_related("definition", "value_choice"), to_attr="feature_values_cache"),
            Prefetch("offering__prices", queryset=PriceRecord.objects.filter(effective_to__isnull=True), to_attr="prices_cache"),
            Prefetch("offering__availability_history", queryset=AvailabilityRecord.objects.filter(effective_to__isnull=True), to_attr="availability_cache"),
            Prefetch("media_links", queryset=ListingMedia.objects.select_related("media").order_by("sort_order"), to_attr="media_cache"),
        ).order_by("-updated_at", "id")

    def create(self, request, *args, **kwargs):
        input_serializer = AdminPropertyAggregateInputSerializer(data=request.data, context={"request": request})
        input_serializer.is_valid(raise_exception=True)
        listing = create_property(input_serializer.validated_data, input_serializer.offering_serializer, request.user, request=request)
        listing = self.get_queryset().get(pk=listing.pk)
        return Response(self.get_serializer(listing).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        existing = self.get_object()
        input_serializer = AdminPropertyAggregateInputSerializer(
            data=request.data,
            partial=kwargs.get("partial", False),
            context={"request": request, "listing": existing, "offering": existing.offering},
        )
        input_serializer.is_valid(raise_exception=True)
        listing = update_property(existing.pk, input_serializer.validated_data, input_serializer.offering_serializer, request.user, request=request)
        listing = self.get_queryset().get(pk=listing.pk)
        return Response(self.get_serializer(listing).data)

    def destroy(self, request, *args, **kwargs):
        archive_property(self.get_object(), request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        listing = get_object_or_404(Listing.all_objects.select_related("offering"), pk=pk)
        listing = restore_property(listing, request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=listing.pk)).data)

    @action(detail=True, methods=["get"], url_path="delete-preview")
    def delete_preview(self, request, pk=None):
        listing = get_object_or_404(Listing.all_objects.select_related("offering"), pk=pk)
        dependencies = property_dependencies(listing)
        dependencies["can_delete"] = listing.archived_at is not None and not any(
            dependencies[key] for key in ("sales", "visits", "inquiries", "interests")
        )
        return Response(dependencies)

    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        listing = get_object_or_404(Listing.all_objects.select_related("offering"), pk=pk)
        if not has_recent_mfa(request):
            return Response({"detail": "Vuelve a verificar tu identidad para continuar."}, status=403)
        hard_delete_property(
            listing, request.user, confirmation=request.data.get("confirmation", ""),
            reason=request.data.get("reason", ""), request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    locations = [{"id": item.id, "name": item.name, "state": item.state.name, "slug": item.location_content.slug} for item in Municipality.objects.filter(is_active=True, location_content__is_featured=True, location_content__archived_at__isnull=True).select_related("state", "location_content")[:12]]
    content = HomeContent.objects.filter(key="main").first()
    return Response({"hero": PublicListingSerializer(featured[:5], many=True, context={"request": request}).data, "featured_listings": PublicListingSerializer(featured, many=True, context={"request": request}).data, "featured_developments": DevelopmentSerializer(developments, many=True).data, "featured_locations": locations, "content": HomeContentSerializer(content).data if content else None})


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
def slug_redirect(request, path):
    redirect = get_object_or_404(SlugRedirect, old_path=f"/{path}")
    return HttpResponsePermanentRedirect(redirect.new_path)
