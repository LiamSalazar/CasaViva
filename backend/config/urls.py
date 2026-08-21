from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponsePermanentRedirect
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.accounts import views as account_views
from apps.analytics import views as analytics_views
from apps.audit.views import AuditViewSet
from apps.catalog import views as catalog_views
from apps.catalog.models import Amenity, Development, PropertyType
from apps.content.views import GuideViewSet, HomeContentViewSet, LocationContentViewSet, PublicGuideViewSet
from apps.crm import views as crm_views
from apps.geo.models import State, Municipality, Locality, Neighborhood
from apps.geo import views as geo_views
from apps.listings import views as listing_views
from apps.marketing.views import CampaignViewSet, SpendViewSet
from apps.media_library.views import upload_media
from drf_spectacular.utils import extend_schema, OpenApiTypes


@extend_schema(operation_id="public_locations", responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([AllowAny])
def locations(request):
    states = []
    for state in State.objects.filter(is_active=True).prefetch_related("municipalities"):
        municipalities = []
        for municipality in state.municipalities.filter(is_active=True).select_related("location_content__hero_media"):
            content = getattr(municipality, "location_content", None)
            if content and content.archived_at:
                content = None
            municipalities.append({
                "id": municipality.id, "name": municipality.name,
                "slug": content.slug if content else None,
                "description": content.description if content else "",
                "heroImage": f"/media/{content.hero_media.storage_key}" if content and content.hero_media_id else None,
                "is_featured": content.is_featured if content else False,
                "latitude": content.latitude if content else None,
                "longitude": content.longitude if content else None,
                "content_id": content.id if content else None,
            })
        states.append({"id": state.id, "name": state.name, "code": state.code, "municipalities": municipalities})
    return Response(states)


@extend_schema(operation_id="public_search_options", responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([AllowAny])
def search_options(request):
    return Response({
        "property_types": list(PropertyType.objects.filter(is_active=True).values("id", "code", "name").order_by("sort_order", "name")),
        "amenities": list(Amenity.objects.filter(is_active=True).values("id", "slug", "name", "category").order_by("sort_order", "name")),
        "locations": [
            {"id": municipality.id, "name": municipality.name, "state_id": municipality.state_id, "state": municipality.state.name}
            for municipality in Municipality.objects.filter(is_active=True).select_related("state").order_by("state__name", "name")
        ],
    })


@extend_schema(operation_id="public_developments", responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([AllowAny])
def developments(request, slug=None):
    qs = Development.objects.filter(is_published=True).select_related("developer", "state", "municipality").prefetch_related("amenities", "media_links__media")
    if slug:
        qs = qs.filter(slug=slug)
        item = qs.first()
        if not item: return Response(status=404)
        items = [item]
    else: items = qs
    data = [{"id": d.id, "slug": d.slug, "name": d.name, "developerName": d.developer.name, "description": d.description, "shortDescription": d.short_description, "state": d.state.name, "municipality": d.municipality.name, "latitude": d.latitude, "longitude": d.longitude, "heroImage": next((f"/media/{x.media.storage_key}" for x in d.media_links.all() if x.role == "HERO"), None), "gallery": [f"/media/{x.media.storage_key}" for x in d.media_links.all()], "amenities": [x.name for x in d.amenities.all()], "published": d.is_published, "featured": d.is_featured} for d in items]
    return Response(data[0] if slug else {"results": data})


public_router = DefaultRouter()
public_router.register("listings", listing_views.PublicListingViewSet, basename="public-listing")
public_router.register("guides", PublicGuideViewSet, basename="public-guide")

admin_router = DefaultRouter()
admin_router.register("developers", catalog_views.DeveloperViewSet)
admin_router.register("developments", catalog_views.DevelopmentViewSet)
admin_router.register("models", catalog_views.HousingModelViewSet)
admin_router.register("development-models", catalog_views.DevelopmentModelViewSet)
admin_router.register("offerings", catalog_views.OfferingViewSet)
admin_router.register("listings", listing_views.ListingViewSet)
admin_router.register("properties", listing_views.PropertyAggregateViewSet, basename="admin-property")
admin_router.register("property-types", catalog_views.PropertyTypeViewSet)
admin_router.register("amenities", catalog_views.AmenityViewSet)
admin_router.register("features", catalog_views.FeatureViewSet)
admin_router.register("states", geo_views.StateViewSet)
admin_router.register("municipalities", geo_views.MunicipalityViewSet)
admin_router.register("localities", geo_views.LocalityViewSet)
admin_router.register("neighborhoods", geo_views.NeighborhoodViewSet)
admin_router.register("leads", crm_views.LeadViewSet)
admin_router.register("inquiries", crm_views.InquiryViewSet)
admin_router.register("visits", crm_views.VisitViewSet)
admin_router.register("sales", crm_views.SaleViewSet)
admin_router.register("guides", GuideViewSet)
admin_router.register("content", HomeContentViewSet)
admin_router.register("location-content", LocationContentViewSet)
admin_router.register("audit", AuditViewSet)
admin_router.register("users", account_views.UserViewSet)
admin_router.register("marketing-campaigns", CampaignViewSet)
admin_router.register("marketing-spend", SpendViewSet)

urlpatterns = [
    path("api/v1/auth/login/", account_views.password_login),
    path("api/v1/auth/mfa/enroll/", account_views.enroll_mfa),
    path("api/v1/auth/mfa/verify/", account_views.verify_mfa),
    path("api/v1/auth/logout/", account_views.logout_view),
    path("api/v1/auth/me/", account_views.me),
    path("api/v1/public/home/", listing_views.public_home),
    path("api/v1/public/locations/", locations),
    path("api/v1/public/search-options/", search_options),
    path("api/v1/public/developments/", developments),
    path("api/v1/public/developments/<slug:slug>/", developments),
    path("api/v1/public/inquiries/", crm_views.public_inquiry),
    path("api/v1/public/analytics/session/", analytics_views.start_session),
    path("api/v1/public/analytics/events/", analytics_views.ingest_event),
    path("api/v1/redirect/<path:path>/", listing_views.slug_redirect),
    path("api/v1/public/", include(public_router.urls)),
    path("api/v1/admin/bi/overview/", analytics_views.bi_overview),
    path("api/v1/admin/bi/sessions/<uuid:session_id>/", analytics_views.session_attribution),
    path("api/v1/admin/bi/listings/", analytics_views.bi_listing_performance),
    path("api/v1/admin/bi/searches/", analytics_views.bi_search_demand),
    path("api/v1/admin/bi/marketing/", analytics_views.bi_marketing),
    path("api/v1/admin/bi/sales/", analytics_views.bi_sales),
    path("api/v1/admin/bi/decisions/", analytics_views.bi_decisions),
    path("api/v1/admin/media/", upload_media),
    path("api/v1/admin/", include(admin_router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]
if settings.ENABLE_TECHNICAL_ADMIN:
    from apps.accounts.admin_site import technical_admin_site
    urlpatterns += [path("_technical-admin/", technical_admin_site.urls)]
if settings.DEBUG:
    urlpatterns += [path("api/schema/docs/", SpectacularSwaggerView.as_view(url_name="schema"))] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
