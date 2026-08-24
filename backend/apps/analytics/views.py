from datetime import datetime, time, timedelta
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.common.throttling import FixedScopeThrottle
from apps.accounts.permissions import CanViewBI, IsMfaVerifiedAdmin
from apps.crm.models import Inquiry, Sale, Visit
from apps.listings.models import Listing
from apps.geo.models import Municipality
from apps.marketing.models import MarketingCampaign, MarketingSpend
from apps.crm.models import Lead
from .models import AnalyticsEvent, AnonymousVisitor, WebSession
from .serializers import EventSerializer, StartSessionSerializer, WebSessionAttributionSerializer
from .attribution import first_touch_session, with_first_touch
from drf_spectacular.utils import extend_schema, OpenApiTypes


class AnalyticsThrottle(FixedScopeThrottle): scope = "analytics"

@extend_schema(request=StartSessionSerializer, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnalyticsThrottle])
def start_session(request):
    serializer = StartSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    now = timezone.now()
    visitor_id = data.pop("visitor_id", None)
    visitor = AnonymousVisitor.objects.filter(pk=visitor_id).first() if visitor_id else None
    if visitor:
        visitor.last_seen_at = now; visitor.save(update_fields=["last_seen_at", "updated_at"])
    else:
        visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    session = WebSession.objects.create(visitor=visitor, started_at=now, last_seen_at=now, **data)
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


@extend_schema(responses={200: WebSessionAttributionSerializer})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def session_attribution(request, session_id):
    try:
        session = WebSession.objects.get(pk=session_id)
    except (WebSession.DoesNotExist, ValueError, TypeError):
        return Response({"detail": "Sesión no encontrada."}, status=404)
    return Response(WebSessionAttributionSerializer(session).data)


def period_bounds(request):
    now = timezone.now()
    period = request.query_params.get("period")
    if period == "current_month":
        end = now
        start = timezone.localtime(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "previous_month":
        end = timezone.localtime(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prior_day = end - timedelta(days=1)
        start = prior_day.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "custom":
        start_date = parse_date(request.query_params.get("start", ""))
        end_date = parse_date(request.query_params.get("end", ""))
        if not start_date or not end_date or end_date < start_date:
            raise ValidationError({"period": "Captura un rango de fechas válido."})
        zone = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(start_date, time.min), zone)
        end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), zone)
    else:
        raw_days = request.query_params.get("days", {"7d": "7", "30d": "30", "90d": "90"}.get(period, "30"))
        try:
            days = min(max(int(raw_days), 1), 366)
        except (TypeError, ValueError):
            raise ValidationError({"days": "Selecciona un periodo válido."})
        end = now
        start = end - timedelta(days=days)
    duration = end - start
    previous = start - duration
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
            "visits": Visit.objects.filter(status=Visit.Status.COMPLETED, completed_at__gte=a, completed_at__lt=b).count(),
            "visits_scheduled": Visit.objects.filter(status=Visit.Status.SCHEDULED, scheduled_at__gte=a, scheduled_at__lt=b).count(),
            "visits_completed": Visit.objects.filter(status=Visit.Status.COMPLETED, completed_at__gte=a, completed_at__lt=b).count(),
            "visits_cancelled": Visit.objects.filter(status=Visit.Status.CANCELLED, scheduled_at__gte=a, scheduled_at__lt=b).count(),
            "visits_no_show": Visit.objects.filter(status=Visit.Status.NO_SHOW, scheduled_at__gte=a, scheduled_at__lt=b).count(),
            "sales": Sale.objects.filter(closed_at__gte=a, closed_at__lt=b, status="CLOSED").count(),
        }
    current, prior = counts(start, end), counts(previous, start)
    traffic = list(WebSession.objects.filter(started_at__gte=start, started_at__lt=end).annotate(date=TruncDate("started_at")).values("date").annotate(sessions=Count("id"), visitors=Count("visitor_id", distinct=True)).order_by("date"))
    funnel = []
    previous_value = None
    for label, key in [("Sesiones", "sessions"), ("Propiedades vistas", "listing_views"), ("Consultas", "inquiries"), ("Visitas realizadas", "visits_completed"), ("Ventas cerradas", "sales")]:
        value = current[key]
        funnel.append({"label": label, "value": value, "conversion_from_previous": round(value / previous_value * 100, 2) if previous_value else None})
        previous_value = value
    inventory = {"registered": Listing.all_objects.count(), "published": Listing.objects.filter(is_published=True).count(), "unpublished": Listing.objects.filter(is_published=False).count(), "archived": Listing.all_objects.filter(archived_at__isnull=False).count()}
    lead_ids = Lead.objects.filter(created_at__gte=start, created_at__lt=end).values_list("id", flat=True)
    cohort = {
        "leads": Lead.objects.filter(id__in=lead_ids).count(),
        "with_visit": Lead.objects.filter(id__in=lead_ids, visits__status=Visit.Status.COMPLETED).distinct().count(),
        "with_closed_sale": Lead.objects.filter(id__in=lead_ids, sales__status="CLOSED").distinct().count(),
    }
    return Response({
        "period": {"start": start, "end": end}, "current": current, "previous": prior,
        "traffic": traffic, "funnel": funnel, "funnel_kind": "period_activity",
        "funnel_description": "Actividad registrada en cada etapa durante el periodo. Las visitas son sólo las marcadas como realizadas; no representa una cohorte única.",
        "lead_cohort": cohort, "inventory": inventory,
    })

@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_listing_performance(request):
    start, end, _ = period_bounds(request)
    rows = Listing.all_objects.annotate(
        views=Count("analytics_events", filter=Q(analytics_events__event_name="listing_viewed", analytics_events__occurred_at__gte=start, analytics_events__occurred_at__lt=end), distinct=True),
        favorite_additions=Count("analytics_events", filter=Q(analytics_events__event_name="favorite_added", analytics_events__occurred_at__gte=start, analytics_events__occurred_at__lt=end), distinct=True),
        inquiries_count=Count("inquiries", filter=Q(inquiries__created_at__gte=start, inquiries__created_at__lt=end), distinct=True),
        visits_scheduled=Count("offering__visits", filter=Q(offering__visits__scheduled_at__gte=start, offering__visits__scheduled_at__lt=end), distinct=True),
        visits_completed=Count("offering__visits", filter=Q(offering__visits__status=Visit.Status.COMPLETED, offering__visits__completed_at__gte=start, offering__visits__completed_at__lt=end), distinct=True),
        sales_count=Count("sales", filter=Q(sales__closed_at__gte=start, sales__closed_at__lt=end, sales__status="CLOSED"), distinct=True),
    ).values("id", "title", "views", "favorite_additions", "inquiries_count", "visits_scheduled", "visits_completed", "sales_count").order_by("-views")[:100]
    listing_ids = [row["id"] for row in rows]
    view_sessions = {}
    for listing_id, session_id in AnalyticsEvent.objects.filter(
        listing_id__in=listing_ids, event_name="listing_viewed",
        occurred_at__gte=start, occurred_at__lt=end,
    ).exclude(session_id__isnull=True).values_list("listing_id", "session_id").distinct():
        view_sessions.setdefault(listing_id, set()).add(session_id)
    inquiry_sessions, inquiry_leads = {}, {}
    for listing_id, session_id, lead_id in Inquiry.objects.filter(
        listing_id__in=listing_ids, created_at__gte=start, created_at__lt=end,
    ).values_list("listing_id", "session_id", "lead_id"):
        inquiry_leads.setdefault(listing_id, set()).add(lead_id)
        if session_id:
            inquiry_sessions.setdefault(listing_id, set()).add(session_id)
    completed_visit_leads, closed_sale_leads = {}, {}
    for listing_id, lead_id in Visit.objects.filter(
        offering__listing__id__in=listing_ids, status=Visit.Status.COMPLETED,
        completed_at__gte=start, completed_at__lt=end,
    ).values_list("offering__listing__id", "lead_id").distinct():
        completed_visit_leads.setdefault(listing_id, set()).add(lead_id)
    for listing_id, lead_id in Sale.objects.filter(
        listing_id__in=listing_ids, status=Sale.Status.CLOSED,
        closed_at__gte=start, closed_at__lt=end,
    ).values_list("listing_id", "lead_id").distinct():
        closed_sale_leads.setdefault(listing_id, set()).add(lead_id)
    result = []
    for row in rows:
        listing_id = row["id"]
        viewed = view_sessions.get(listing_id, set())
        inquiry_session_people = inquiry_sessions.get(listing_id, set()) & viewed
        inquiry_people = inquiry_leads.get(listing_id, set())
        visit_people = completed_visit_leads.get(listing_id, set()) & inquiry_people
        sale_people = closed_sale_leads.get(listing_id, set()) & visit_people
        row["unique_view_sessions"] = len(viewed)
        row["unique_inquiry_sessions"] = len(inquiry_session_people)
        row["unique_inquiry_leads"] = len(inquiry_people)
        row["unique_completed_visit_leads"] = len(visit_people)
        row["unique_closed_sale_leads"] = len(sale_people)
        row["view_to_inquiry_rate"] = round(len(inquiry_session_people) / len(viewed) * 100, 2) if viewed else None
        row["inquiry_to_visit_rate"] = round(len(visit_people) / len(inquiry_people) * 100, 2) if inquiry_people else None
        row["visit_to_sale_rate"] = round(len(sale_people) / len(visit_people) * 100, 2) if visit_people else None
        result.append(row)
    return Response(result)


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_search_demand(request):
    start, end, _ = period_bounds(request)
    municipality_ids, price_ranges, bedrooms, property_types = {}, {}, {}, {}
    filters, no_results = {}, 0
    for properties in AnalyticsEvent.objects.filter(occurred_at__gte=start, occurred_at__lt=end, event_name="search_performed").values_list("properties", flat=True):
        if properties.get("result_count") == 0:
            no_results += 1
        for value in properties.get("municipality_ids") or []:
            municipality_ids[str(value)] = municipality_ids.get(str(value), 0) + 1
        if properties.get("price_min") is not None or properties.get("price_max") is not None:
            label = f"{properties.get('price_min') or '—'} – {properties.get('price_max') or '—'}"
            price_ranges[label] = price_ranges.get(label, 0) + 1
        if properties.get("bedrooms_min") is not None:
            value = str(properties["bedrooms_min"]); bedrooms[value] = bedrooms.get(value, 0) + 1
        for value in properties.get("property_type_codes") or []:
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
    start, end, _ = period_bounds(request)
    raw_horizon = request.query_params.get("horizon", "90")
    if raw_horizon == "lifetime":
        horizon_days = None
    else:
        try:
            horizon_days = int(raw_horizon)
        except (TypeError, ValueError):
            raise ValidationError({"horizon": "Selecciona 30, 60, 90 o lifetime."})
        if horizon_days not in (30, 60, 90):
            raise ValidationError({"horizon": "Selecciona 30, 60, 90 o lifetime."})

    acquired = with_first_touch(Lead.objects.all()).filter(acquired_at__gte=start, acquired_at__lt=end)

    def cohort_metrics(lead_rows):
        acquisition = {row["id"]: row["acquired_at"] for row in lead_rows}
        lead_ids = list(acquisition)
        if not lead_ids:
            return {"inquiries": 0, "completed_visits": 0, "closed_sales": 0, "revenue": None, "commission": None}
        def within(lead_id, occurred_at):
            acquired_at = acquisition[lead_id]
            return occurred_at >= acquired_at and (
                horizon_days is None or occurred_at < acquired_at + timedelta(days=horizon_days)
            )
        inquiries = sum(
            within(lead_id, created_at)
            for lead_id, created_at in Inquiry.objects.filter(lead_id__in=lead_ids).values_list("lead_id", "created_at")
        )
        visits = sum(
            within(lead_id, completed_at)
            for lead_id, completed_at in Visit.objects.filter(
                lead_id__in=lead_ids, status=Visit.Status.COMPLETED, completed_at__isnull=False,
            ).values_list("lead_id", "completed_at")
        )
        sales = [
            (lead_id, closed_at, sale_price, commission_amount)
            for lead_id, closed_at, sale_price, commission_amount in Sale.objects.filter(
                lead_id__in=lead_ids, status=Sale.Status.CLOSED,
            ).values_list("lead_id", "closed_at", "sale_price", "commission_amount")
            if within(lead_id, closed_at)
        ]
        return {
            "inquiries": inquiries,
            "completed_visits": visits,
            "closed_sales": len(sales),
            "revenue": sum((row[2] for row in sales), start=0) if sales else None,
            "commission": sum((row[3] or 0 for row in sales), start=0) if sales else None,
        }

    campaign_codes = set(WebSession.objects.filter(started_at__gte=start, started_at__lt=end).exclude(utm_campaign__isnull=True).exclude(utm_campaign="").values_list("utm_campaign", flat=True))
    campaign_codes.update(acquired.exclude(acquired_campaign__isnull=True).values_list("acquired_campaign", flat=True))
    campaign_codes.update(MarketingCampaign.all_objects.values_list("utm_campaign", flat=True))
    campaigns = []
    spend_end = (end - timedelta(microseconds=1)).date()
    for code in sorted(campaign_codes):
        lead_rows = list(acquired.filter(acquired_campaign=code).values("id", "acquired_at"))
        lead_ids = [row["id"] for row in lead_rows]
        sessions = WebSession.objects.filter(started_at__gte=start, started_at__lt=end, utm_campaign=code).count()
        metrics = cohort_metrics(lead_rows)
        inquiries = metrics["inquiries"]
        completed_visits, closed_sales = metrics["completed_visits"], metrics["closed_sales"]
        campaign = MarketingCampaign.all_objects.filter(utm_campaign=code).first()
        spend = MarketingSpend.objects.filter(
            campaign=campaign, is_voided=False, date__gte=start.date(), date__lte=spend_end,
        ).aggregate(value=Sum("amount"))["value"] if campaign else None
        campaigns.append({
            "utm_campaign": code, "sessions": sessions, "leads": len(lead_ids),
            "inquiries": inquiries, "completed_visits": completed_visits,
            "closed_sales": closed_sales, "spend": spend,
            "cost_per_lead": spend / len(lead_ids) if spend is not None and lead_ids else None,
            "cost_per_inquiry": spend / inquiries if spend is not None and inquiries else None,
            "cost_per_completed_visit": spend / completed_visits if spend is not None and completed_visits else None,
            "cost_per_sale": spend / closed_sales if spend is not None and closed_sales else None,
            "attributable_revenue": metrics["revenue"], "attributable_commission": metrics["commission"],
        })

    creative_groups = WebSession.objects.filter(started_at__gte=start, started_at__lt=end).values(
        "utm_source", "utm_medium", "utm_campaign", "utm_content",
    ).annotate(sessions=Count("id")).order_by("-sessions")[:100]
    creatives = []
    for group in creative_groups:
        lead_rows = list(acquired.filter(
            acquired_source=group["utm_source"], acquired_medium=group["utm_medium"],
            acquired_campaign=group["utm_campaign"], acquired_content=group["utm_content"],
        ).values("id", "acquired_at"))
        metrics = cohort_metrics(lead_rows)
        creatives.append({
            **group, "views": AnalyticsEvent.objects.filter(
                session__started_at__gte=start, session__started_at__lt=end,
                session__utm_source=group["utm_source"], session__utm_medium=group["utm_medium"],
                session__utm_campaign=group["utm_campaign"], session__utm_content=group["utm_content"],
                event_name="listing_viewed",
            ).count(),
            "inquiries": metrics["inquiries"],
            "completed_visits": metrics["completed_visits"],
            "closed_sales": metrics["closed_sales"],
            "spend": None,
        })

    sales_rows = {}
    period_sales = Sale.objects.filter(status=Sale.Status.CLOSED, closed_at__gte=start, closed_at__lt=end).select_related("lead")
    for sale in period_sales:
        session = first_touch_session(sale.lead)
        key = (session.utm_campaign if session else None, session.utm_source if session else None, session.utm_medium if session else None)
        row = sales_rows.setdefault(key, {"utm_campaign": key[0], "utm_source": key[1], "utm_medium": key[2], "closed_sales": 0, "revenue": 0, "commission": 0})
        row["closed_sales"] += 1
        row["revenue"] += sale.sale_price
        row["commission"] += sale.commission_amount or 0
    return Response({
        "attribution_model": "first_touch", "horizon_days": horizon_days,
        "campaigns": campaigns, "creatives": creatives,
        "sales_by_origin": list(sales_rows.values()),
    })


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_sales(request):
    start, end, _ = period_bounds(request)
    qs = Sale.objects.filter(closed_at__gte=start, closed_at__lt=end, status="CLOSED")
    timeline = list(qs.annotate(date=TruncDate("closed_at")).values("date").annotate(sales=Count("id"), value=Sum("sale_price"), commissions=Sum("commission_amount")).order_by("date"))
    totals = qs.aggregate(sales=Count("id"), value=Sum("sale_price"), commissions=Sum("commission_amount"))
    durations = [(sale.closed_at - sale.lead.created_at).total_seconds() / 86400 for sale in qs.select_related("lead")]
    totals["average_close_days"] = round(sum(durations) / len(durations), 1) if durations else None
    return Response({"totals": totals, "timeline": timeline})


@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([IsMfaVerifiedAdmin, CanViewBI])
def bi_decisions(request):
    start, end, _ = period_bounds(request)
    performance = list(Listing.all_objects.annotate(views=Count("analytics_events", filter=Q(analytics_events__event_name="listing_viewed", analytics_events__occurred_at__gte=start, analytics_events__occurred_at__lt=end), distinct=True), inquiries_count=Count("inquiries", filter=Q(inquiries__created_at__gte=start, inquiries__created_at__lt=end), distinct=True)).values("id", "title", "views", "inquiries_count").order_by("-views")[:20])
    return Response({"most_inquired": sorted(performance, key=lambda item: -item["inquiries_count"])[:10], "high_views_low_inquiries": [item for item in performance if item["views"] >= 5 and item["inquiries_count"] / item["views"] < .05], "pending_leads": Lead.objects.filter(status__in=["NEW", "CONTACTED"]).count(), "recent_unpublished": Listing.objects.filter(is_published=False, updated_at__gte=start, updated_at__lt=end).count()})
