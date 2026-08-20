from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from apps.accounts.permissions import CanViewBI, IsMfaVerifiedAdmin
from apps.crm.models import Inquiry, Sale, Visit
from apps.listings.models import Listing
from apps.geo.models import Municipality
from apps.marketing.models import MarketingCampaign, MarketingSpend
from apps.crm.models import Lead
from .models import AnalyticsEvent, AnonymousVisitor, WebSession
from .serializers import EventSerializer
from drf_spectacular.utils import extend_schema, OpenApiTypes


class AnalyticsThrottle(ScopedRateThrottle): scope = "analytics"

@extend_schema(request=OpenApiTypes.OBJECT, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
def start_session(request):
    now = timezone.now()
    visitor_id = request.data.get("visitor_id")
    visitor = AnonymousVisitor.objects.filter(pk=visitor_id).first() if visitor_id else None
    if visitor:
        visitor.last_seen_at = now; visitor.save(update_fields=["last_seen_at", "updated_at"])
    else:
        visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    session = WebSession.objects.create(visitor=visitor, started_at=now, last_seen_at=now, landing_path=request.data.get("landing_path", "/")[:500], consent_state=request.data.get("consent_state", "ESSENTIAL")[:30], utm_source=request.data.get("utm_source"), utm_medium=request.data.get("utm_medium"), utm_campaign=request.data.get("utm_campaign"), utm_content=request.data.get("utm_content"), utm_term=request.data.get("utm_term"), referrer_domain=request.data.get("referrer_domain"), device_category=request.data.get("device_category"))
    return Response({"visitor_id": visitor.id, "session_id": session.id}, status=201)

@extend_schema(request=EventSerializer, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnalyticsThrottle])
def ingest_event(request):
    serializer = EventSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    event = serializer.save()
    WebSession.objects.filter(pk=event.session_id).update(last_seen_at=timezone.now())
    return Response({"id": event.id}, status=201)


def period_bounds(request):
    days = min(max(int(request.query_params.get("days", 30)), 1), 366)
    end = timezone.now(); start = end - timedelta(days=days); previous = start - timedelta(days=days)
    return start, end, previous

@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_overview(request):
    start, end, previous = period_bounds(request)
    def counts(a, b):
        return {
            "visitors": WebSession.objects.filter(started_at__gte=a, started_at__lt=b).values("visitor_id").distinct().count(),
            "sessions": WebSession.objects.filter(started_at__gte=a, started_at__lt=b).count(),
            "listing_views": AnalyticsEvent.objects.filter(occurred_at__gte=a, occurred_at__lt=b, event_name="listing_viewed").count(),
            "inquiries": Inquiry.objects.filter(created_at__gte=a, created_at__lt=b).count(),
            "visits": Visit.objects.filter(created_at__gte=a, created_at__lt=b).count(),
            "sales": Sale.objects.filter(closed_at__gte=a, closed_at__lt=b, status="CLOSED").count(),
        }
    current, prior = counts(start, end), counts(previous, start)
    traffic = list(WebSession.objects.filter(started_at__gte=start).annotate(date=TruncDate("started_at")).values("date").annotate(sessions=Count("id"), visitors=Count("visitor_id", distinct=True)).order_by("date"))
    funnel = [{"label": labels, "value": current[key]} for labels, key in [("Sesiones", "sessions"), ("Propiedades vistas", "listing_views"), ("Consultas", "inquiries"), ("Visitas", "visits"), ("Ventas", "sales")]]
    inventory = {"registered": Listing.all_objects.count(), "published": Listing.objects.filter(is_published=True).count(), "unpublished": Listing.objects.filter(is_published=False).count(), "archived": Listing.all_objects.filter(archived_at__isnull=False).count()}
    return Response({"period": {"start": start, "end": end}, "current": current, "previous": prior, "traffic": traffic, "funnel": funnel, "inventory": inventory})

@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_listing_performance(request):
    start, _, _ = period_bounds(request)
    rows = Listing.all_objects.annotate(views=Count("analytics_events", filter=Q(analytics_events__event_name="listing_viewed", analytics_events__occurred_at__gte=start), distinct=True), inquiries_count=Count("inquiries", filter=Q(inquiries__created_at__gte=start), distinct=True), sales_count=Count("sales", filter=Q(sales__closed_at__gte=start), distinct=True)).values("id", "title", "views", "inquiries_count", "sales_count").order_by("-views")[:100]
    return Response(list(rows))


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_search_demand(request):
    start, _, _ = period_bounds(request)
    municipality_ids, price_ranges, bedrooms, property_types = {}, {}, {}, {}
    filters, no_results = {}, 0
    for properties in AnalyticsEvent.objects.filter(occurred_at__gte=start, event_name="search_performed").values_list("properties", flat=True):
        if properties.get("result_count") == 0:
            no_results += 1
        for value in properties.get("municipality_ids") or []:
            municipality_ids[str(value)] = municipality_ids.get(str(value), 0) + 1
        if properties.get("price_min") is not None or properties.get("price_max") is not None:
            label = f"{properties.get('price_min') or '—'} – {properties.get('price_max') or '—'}"
            price_ranges[label] = price_ranges.get(label, 0) + 1
        if properties.get("bedrooms_min") is not None:
            value = str(properties["bedrooms_min"]); bedrooms[value] = bedrooms.get(value, 0) + 1
        for value in properties.get("property_type_ids") or []:
            property_types[str(value)] = property_types.get(str(value), 0) + 1
        for key, value in properties.items():
            if value not in (None, "", [], False, 0, "0") and key != "result_count":
                filters[key] = filters.get(key, 0) + 1
    names = {str(x.id): x.name for x in Municipality.objects.filter(id__in=municipality_ids)}
    ranked = lambda values: [{"label": key, "count": count} for key, count in sorted(values.items(), key=lambda item: -item[1])[:20]]
    return Response({"municipalities": ranked({names.get(key, key): value for key, value in municipality_ids.items()}), "price_ranges": ranked(price_ranges), "bedrooms": ranked(bedrooms), "property_types": ranked(property_types), "filters": ranked(filters), "no_results": no_results})


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_marketing(request):
    start, _, _ = period_bounds(request)
    groups = WebSession.objects.filter(started_at__gte=start).values("utm_source", "utm_medium", "utm_campaign", "utm_content").annotate(sessions=Count("id")).order_by("-sessions")[:50]
    result = []
    for group in groups:
        criteria = {key: group[key] for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content")}
        session_ids = WebSession.objects.filter(started_at__gte=start, **criteria).values_list("id", flat=True)
        inquiries = Inquiry.objects.filter(created_at__gte=start, session_id__in=session_ids).count()
        lead_ids = WebSession.objects.filter(id__in=session_ids, lead__isnull=False).values_list("lead_id", flat=True)
        visits = Visit.objects.filter(created_at__gte=start, lead_id__in=lead_ids).count()
        sales = Sale.objects.filter(closed_at__gte=start, lead_id__in=lead_ids, status="CLOSED").count()
        campaign = MarketingCampaign.objects.filter(utm_campaign=group["utm_campaign"]).first() if group["utm_campaign"] else None
        spend = MarketingSpend.objects.filter(campaign=campaign, date__gte=start.date()).aggregate(value=Sum("amount"))["value"] if campaign else None
        result.append({**group, "inquiries": inquiries, "visits": visits, "sales": sales, "spend": spend, "cost_per_inquiry": spend / inquiries if spend is not None and inquiries else None, "cost_per_visit": spend / visits if spend is not None and visits else None, "cost_per_sale": spend / sales if spend is not None and sales else None})
    return Response(result)


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_sales(request):
    start, _, _ = period_bounds(request)
    qs = Sale.objects.filter(closed_at__gte=start, status="CLOSED")
    timeline = list(qs.annotate(date=TruncDate("closed_at")).values("date").annotate(sales=Count("id"), value=Sum("sale_price"), commissions=Sum("commission_amount")).order_by("date"))
    totals = qs.aggregate(sales=Count("id"), value=Sum("sale_price"), commissions=Sum("commission_amount"))
    durations = [(sale.closed_at - sale.lead.created_at).total_seconds() / 86400 for sale in qs.select_related("lead")]
    totals["average_close_days"] = round(sum(durations) / len(durations), 1) if durations else None
    return Response({"totals": totals, "timeline": timeline})


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_decisions(request):
    start, _, _ = period_bounds(request)
    performance = list(Listing.all_objects.annotate(views=Count("analytics_events", filter=Q(analytics_events__event_name="listing_viewed", analytics_events__occurred_at__gte=start), distinct=True), inquiries_count=Count("inquiries", filter=Q(inquiries__created_at__gte=start), distinct=True)).values("id", "title", "views", "inquiries_count").order_by("-views")[:20])
    return Response({"most_inquired": sorted(performance, key=lambda item: -item["inquiries_count"])[:10], "high_views_low_inquiries": [item for item in performance if item["views"] >= 5 and item["inquiries_count"] / item["views"] < .05], "pending_leads": Lead.objects.filter(status__in=["NEW", "CONTACTED"]).count(), "recent_unpublished": Listing.objects.filter(is_published=False, updated_at__gte=start).count()})
