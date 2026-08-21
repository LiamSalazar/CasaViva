import pytest
from django.utils import timezone
from datetime import timedelta
from apps.analytics.models import AnalyticsEvent, AnonymousVisitor, WebSession
from apps.crm.models import Inquiry, Lead, Sale, Visit
from apps.marketing.models import MarketingCampaign, MarketingSpend


@pytest.mark.django_db
def test_analytics_rejects_unknown_and_invalid_payload(client):
    visitor = AnonymousVisitor.objects.create(first_seen_at=timezone.now(), last_seen_at=timezone.now())
    session = WebSession.objects.create(visitor=visitor, started_at=timezone.now(), last_seen_at=timezone.now(), landing_path="/", consent_state="ESSENTIAL")
    base = {"occurred_at": timezone.now().isoformat(), "visitor_id": str(visitor.id), "session_id": str(session.id), "schema_version": 1, "properties": {}}
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "invented_event"}, content_type="application/json").status_code == 400
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "filter_applied"}, content_type="application/json").status_code == 400
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "page_viewed", "page_path": "/"}, content_type="application/json").status_code == 201
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "page_viewed", "schema_version": 99}, content_type="application/json").status_code == 400
    assert client.post("/api/v1/public/analytics/events/", {**base, "event_name": "page_viewed", "properties": {"large": "x" * 17000}}, content_type="application/json").status_code == 400


@pytest.mark.django_db
def test_every_controlled_event_schema_accepts_its_valid_shape(client):
    visitor = AnonymousVisitor.objects.create(first_seen_at=timezone.now(), last_seen_at=timezone.now())
    session = WebSession.objects.create(visitor=visitor, started_at=timezone.now(), last_seen_at=timezone.now(), landing_path="/", consent_state="ESSENTIAL")
    event_names = [
        "page_viewed", "search_performed", "filter_applied", "listing_viewed", "development_viewed",
        "gallery_opened", "favorite_added", "favorite_removed", "recommendation_started",
        "recommendation_completed", "recommendation_result_clicked", "contact_form_opened",
        "contact_form_submitted", "whatsapp_clicked", "phone_clicked", "lead_created",
        "lead_status_changed", "visit_scheduled", "visit_completed", "sale_closed",
    ]
    for event_name in event_names:
        properties = {"filter": "price"} if event_name == "filter_applied" else {"status": "CONTACTED"} if event_name == "lead_status_changed" else {}
        response = client.post(
            "/api/v1/public/analytics/events/",
            {"occurred_at": timezone.now().isoformat(), "visitor_id": str(visitor.id), "session_id": str(session.id), "schema_version": 1, "event_name": event_name, "properties": properties},
            content_type="application/json",
        )
        assert response.status_code == 201, (event_name, response.data)


@pytest.mark.django_db
def test_bi_overview_returns_exact_known_funnel(admin_client, owner, catalog):
    now = timezone.now()
    visitors = [AnonymousVisitor(first_seen_at=now, last_seen_at=now) for _ in range(100)]
    AnonymousVisitor.objects.bulk_create(visitors)
    sessions = [WebSession(visitor=visitor, started_at=now, last_seen_at=now, landing_path="/", consent_state="ESSENTIAL") for visitor in visitors]
    WebSession.objects.bulk_create(sessions)
    AnalyticsEvent.objects.bulk_create([
        AnalyticsEvent(
            occurred_at=now, event_name="listing_viewed", schema_version=1,
            visitor=visitors[index], session=sessions[index], listing=catalog["listing"],
            offering=catalog["offering"], properties={},
        )
        for index in range(60)
    ])
    leads = [Lead.objects.create(first_name=f"Lead {index}") for index in range(10)]
    for index, lead in enumerate(leads):
        Inquiry.objects.create(lead=lead, listing=catalog["listing"], channel="WEB", session_id=sessions[index].id)
    for lead in leads[:5]:
        Visit.objects.create(lead=lead, offering=catalog["offering"], scheduled_at=now)
    for lead in leads[:2]:
        Sale.objects.create(lead=lead, offering=catalog["offering"], listing=catalog["listing"], sale_price=1_000_000, closed_at=now, created_by=owner)

    response = admin_client.get("/api/v1/admin/bi/overview/?period=7d")
    assert response.status_code == 200
    assert response.data["current"] == {
        "visitors": 100, "sessions": 100, "listing_views": 60,
        "inquiries": 10, "visits": 5, "sales": 2,
    }
    assert [row["conversion_from_previous"] for row in response.data["funnel"]] == [None, 60.0, 16.67, 50.0, 40.0]


@pytest.mark.django_db
def test_bi_periods_and_invalid_custom_range(admin_client):
    now = timezone.now()
    visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    for started_at in [now - timedelta(days=6), now - timedelta(days=29), now - timedelta(days=89), now - timedelta(days=120)]:
        WebSession.objects.create(visitor=visitor, started_at=started_at, last_seen_at=started_at, landing_path="/", consent_state="ESSENTIAL")
    assert admin_client.get("/api/v1/admin/bi/overview/?period=7d").data["current"]["sessions"] == 1
    assert admin_client.get("/api/v1/admin/bi/overview/?period=30d").data["current"]["sessions"] == 2
    assert admin_client.get("/api/v1/admin/bi/overview/?period=90d").data["current"]["sessions"] == 3
    assert admin_client.get("/api/v1/admin/bi/overview/?period=custom&start=2026-08-20&end=2026-08-01").status_code == 400
    assert admin_client.get("/api/v1/admin/bi/overview/?days=not-a-number").status_code == 400


@pytest.mark.django_db
def test_bi_detail_endpoints_calculate_search_marketing_sales_and_decisions(admin_client, owner, catalog):
    now = timezone.now()
    visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    lead = Lead.objects.create(first_name="Campaña", status="NEW")
    session = WebSession.objects.create(
        visitor=visitor, lead=lead, started_at=now, last_seen_at=now,
        landing_path="/propiedades", consent_state="ESSENTIAL",
        utm_source="google", utm_medium="cpc", utm_campaign="agosto", utm_content="duplex",
    )
    AnalyticsEvent.objects.create(
        occurred_at=now, event_name="search_performed", schema_version=1,
        visitor=visitor, session=session,
        properties={
            "municipality_ids": [str(catalog["municipality"].id)], "price_min": 800000,
            "price_max": 1500000, "bedrooms_min": 3, "property_type_ids": [str(catalog["offering"].property_type_id)],
            "result_count": 0,
        },
    )
    for _ in range(6):
        AnalyticsEvent.objects.create(
            occurred_at=now, event_name="listing_viewed", schema_version=1,
            visitor=visitor, session=session, listing=catalog["listing"], offering=catalog["offering"], properties={},
        )
    Inquiry.objects.create(lead=lead, listing=catalog["listing"], channel="WEB", session_id=session.id)
    Visit.objects.create(lead=lead, offering=catalog["offering"], scheduled_at=now)
    Sale.objects.create(
        lead=lead, offering=catalog["offering"], listing=catalog["listing"], sale_price=1_200_000,
        commission_rate=3, commission_amount=36_000, closed_at=now, created_by=owner,
    )
    campaign = MarketingCampaign.objects.create(
        name="Agosto", utm_campaign="agosto", channel="Search", start_date=now.date(),
        created_by=owner, updated_by=owner,
    )
    MarketingSpend.objects.create(campaign=campaign, date=now.date(), amount=1000)

    listings = admin_client.get("/api/v1/admin/bi/listings/?period=7d")
    searches = admin_client.get("/api/v1/admin/bi/searches/?period=7d")
    marketing = admin_client.get("/api/v1/admin/bi/marketing/?period=7d")
    sales = admin_client.get("/api/v1/admin/bi/sales/?period=7d")
    decisions = admin_client.get("/api/v1/admin/bi/decisions/?period=7d")
    assert listings.status_code == searches.status_code == marketing.status_code == sales.status_code == decisions.status_code == 200
    assert listings.data[0]["views"] == 6
    assert searches.data["no_results"] == 1
    assert searches.data["municipalities"][0]["label"] == catalog["municipality"].name
    assert marketing.data[0]["spend"] == 1000
    assert marketing.data[0]["cost_per_inquiry"] == 1000
    assert sales.data["totals"]["sales"] == 1
    assert decisions.data["pending_leads"] == 1
