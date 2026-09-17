import pytest
from django.test import override_settings
from django.utils import timezone
from datetime import datetime, timedelta
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
def test_start_session_validates_uuid_lengths_enums_and_required_types(client):
    valid = client.post(
        "/api/v1/public/analytics/session/",
        {"landing_path": "/?utm_campaign=agosto", "utm_source": "instagram", "utm_medium": "paid_social", "utm_campaign": "agosto", "utm_content": "reel_04", "device_category": "mobile", "consent_state": "SESSION_ANALYTICS"},
        format="json",
    )
    assert valid.status_code == 201, valid.data
    visitor_id = valid.data["visitor_id"]
    assert client.post("/api/v1/public/analytics/session/", {"visitor_id": "not-a-uuid", "landing_path": "/", "consent_state": "SESSION_ANALYTICS"}, format="json").status_code == 400
    assert client.post("/api/v1/public/analytics/session/", {"visitor_id": visitor_id, "landing_path": "/", "utm_source": "x" * 121, "consent_state": "SESSION_ANALYTICS"}, format="json").status_code == 400
    assert client.post("/api/v1/public/analytics/session/", {"visitor_id": visitor_id, "landing_path": "/", "device_category": "watch", "consent_state": "SESSION_ANALYTICS"}, format="json").status_code == 400
    assert client.post("/api/v1/public/analytics/session/", {"visitor_id": visitor_id, "landing_path": "/", "consent_state": "UNKNOWN"}, format="json").status_code == 400
    assert client.post("/api/v1/public/analytics/session/", {"visitor_id": str(visitor_id), "landing_path": []}, content_type="application/json").status_code == 400


@pytest.mark.django_db
def test_admin_can_read_session_attribution(admin_client):
    now = timezone.now()
    visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    lead = Lead.objects.create(first_name="Atribución")
    session = WebSession.objects.create(
        visitor=visitor, lead=lead, started_at=now, last_seen_at=now,
        landing_path="/?utm_campaign=tecamac", consent_state="ESSENTIAL",
        utm_source="instagram", utm_campaign="tecamac",
    )
    response = admin_client.get(f"/api/v1/admin/bi/sessions/{session.id}/")
    assert response.status_code == 200
    assert response.data["lead_id"] == lead.id
    assert response.data["utm_campaign"] == "tecamac"


@pytest.mark.django_db
def test_start_session_is_throttled(client, monkeypatch):
    from django.core.cache import cache
    from apps.analytics.views import AnalyticsThrottle

    cache.clear()
    monkeypatch.setattr(AnalyticsThrottle, "THROTTLE_RATES", {"analytics": "1/min"})
    first = client.post("/api/v1/public/analytics/session/", {"landing_path": "/", "consent_state": "SESSION_ANALYTICS"}, format="json")
    second = client.post("/api/v1/public/analytics/session/", {"landing_path": "/", "consent_state": "SESSION_ANALYTICS"}, format="json")
    assert first.status_code == 201
    assert second.status_code == 429


@pytest.mark.django_db
def test_limited_session_rejects_analytics_events(client):
    response = client.post(
        "/api/v1/public/analytics/session/",
        {"landing_path": "/", "consent_state": "LIMITED"},
        format="json",
    )
    assert response.status_code == 201
    payload = response.data
    event = client.post(
        "/api/v1/public/analytics/events/",
        {
            "occurred_at": timezone.now().isoformat(), "event_name": "page_viewed",
            "schema_version": 1, "visitor_id": payload["visitor_id"],
            "session_id": payload["session_id"], "page_path": "/", "properties": {},
        },
        format="json",
    )
    assert event.status_code == 400


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
        Visit.objects.create(lead=lead, offering=catalog["offering"], scheduled_at=now, status="COMPLETED", completed_at=now)
    for lead in leads[:2]:
        Sale.objects.create(lead=lead, offering=catalog["offering"], listing=catalog["listing"], sale_price=1_000_000, closed_at=now, created_by=owner)

    response = admin_client.get("/api/v1/admin/bi/overview/?period=7d")
    assert response.status_code == 200
    assert response.data["current"] == {
        "visitors": 100, "sessions": 100, "listing_views": 60,
        "inquiries": 10, "visits": 5, "visits_scheduled": 0,
        "visits_completed": 5, "visits_cancelled": 0, "visits_no_show": 0,
        "sales": 2,
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
            "price_max": 1500000, "bedrooms_min": 3, "property_type_codes": [catalog["offering"].property_type.code],
            "result_count": 0,
        },
    )
    for _ in range(6):
        AnalyticsEvent.objects.create(
            occurred_at=now, event_name="listing_viewed", schema_version=1,
            visitor=visitor, session=session, listing=catalog["listing"], offering=catalog["offering"], properties={},
        )
    Inquiry.objects.create(lead=lead, listing=catalog["listing"], channel="WEB", session_id=session.id)
    Visit.objects.create(lead=lead, offering=catalog["offering"], scheduled_at=now, status="COMPLETED", completed_at=now)
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
    assert marketing.data["campaigns"][0]["spend"] == 1000
    assert marketing.data["campaigns"][0]["cost_per_inquiry"] == 1000
    assert sales.data["totals"]["sales"] == 1
    assert decisions.data["pending_leads"] == 1
    assert listings.data[0]["favorite_additions"] == 0
    assert listings.data[0]["visits_completed"] == 1
    assert listings.data[0]["inquiry_to_visit_rate"] == 100.0
    assert listings.data[0]["visit_to_sale_rate"] == 100.0


@pytest.mark.django_db
def test_events_before_and_after_inquiry_share_the_same_lead(client, catalog):
    from django.core.management import call_command
    call_command("seed_system")
    now = timezone.now()
    visitor = AnonymousVisitor.objects.create(first_seen_at=now, last_seen_at=now)
    session = WebSession.objects.create(visitor=visitor, started_at=now, last_seen_at=now, landing_path="/", consent_state="ESSENTIAL")
    base = {"occurred_at": now.isoformat(), "event_name": "page_viewed", "schema_version": 1, "visitor_id": str(visitor.id), "session_id": str(session.id), "properties": {}}
    before = client.post("/api/v1/public/analytics/events/", base, format="json")
    inquiry = client.post("/api/v1/public/inquiries/", {"first_name": "Cliente", "email": "eventos@example.test", "privacy_consent": True, "session_id": str(session.id), "visitor_id": str(visitor.id)}, format="json")
    after = client.post("/api/v1/public/analytics/events/", base, format="json")
    assert before.status_code == inquiry.status_code == after.status_code == 201
    lead = Inquiry.objects.get(pk=inquiry.data["id"]).lead
    assert list(AnalyticsEvent.objects.order_by("received_at").values_list("lead_id", flat=True)) == [lead.id, lead.id]


@pytest.mark.django_db
def test_deferred_attribution_and_campaign_spend_are_not_duplicated(admin_client, owner, catalog):
    from datetime import datetime
    zone = timezone.get_current_timezone()
    acquired_at = timezone.make_aware(datetime(2026, 6, 1, 12), zone)
    sold_at = timezone.make_aware(datetime(2026, 7, 15, 12), zone)
    visitor = AnonymousVisitor.objects.create(first_seen_at=acquired_at, last_seen_at=sold_at)
    leads = []
    for content in ("creative_1", "creative_2", "creative_3"):
        lead = Lead.objects.create(first_name=content)
        leads.append(lead)
        WebSession.objects.create(visitor=visitor, lead=lead, started_at=acquired_at, last_seen_at=acquired_at, landing_path="/", consent_state="ESSENTIAL", utm_source="instagram", utm_medium="paid_social", utm_campaign="campaign_a", utm_content=content)
    Inquiry.objects.create(lead=leads[0], channel="WEB")
    Visit.objects.create(lead=leads[0], offering=catalog["offering"], scheduled_at=acquired_at, status="COMPLETED", completed_at=acquired_at + timedelta(days=9))
    Sale.objects.create(lead=leads[0], offering=catalog["offering"], listing=catalog["listing"], sale_price=1_000_000, closed_at=sold_at, created_by=owner)
    campaign = MarketingCampaign.objects.create(name="Campaign A", utm_campaign="campaign_a", channel="Social", start_date=acquired_at.date(), created_by=owner, updated_by=owner)
    MarketingSpend.objects.create(campaign=campaign, date=acquired_at.date(), amount=3000)

    cohort = admin_client.get("/api/v1/admin/bi/marketing/?period=custom&start=2026-06-01&end=2026-06-30&horizon=60")
    sales_period = admin_client.get("/api/v1/admin/bi/marketing/?period=custom&start=2026-07-01&end=2026-07-31&horizon=lifetime")
    assert cohort.status_code == sales_period.status_code == 200
    assert cohort.data["campaigns"][0]["spend"] == 3000
    assert cohort.data["campaigns"][0]["closed_sales"] == 1
    assert len(cohort.data["creatives"]) == 3
    assert all(row["spend"] is None for row in cohort.data["creatives"])
    assert sales_period.data["sales_by_origin"][0]["utm_campaign"] == "campaign_a"
    assert sales_period.data["sales_by_origin"][0]["closed_sales"] == 1


@pytest.mark.django_db
def test_marketing_horizon_is_calculated_from_each_lead_acquisition(admin_client, owner, catalog):
    zone = timezone.get_current_timezone()
    acquired_a = timezone.make_aware(datetime(2026, 8, 1, 12), zone)
    acquired_b = timezone.make_aware(datetime(2026, 8, 31, 12), zone)
    visitor_a = AnonymousVisitor.objects.create(first_seen_at=acquired_a, last_seen_at=acquired_a)
    visitor_b = AnonymousVisitor.objects.create(first_seen_at=acquired_b, last_seen_at=acquired_b)
    lead_a = Lead.objects.create(first_name="Fuera")
    lead_b = Lead.objects.create(first_name="Dentro")
    for visitor, lead, acquired, content in [
        (visitor_a, lead_a, acquired_a, "content_a"),
        (visitor_b, lead_b, acquired_b, "content_b"),
    ]:
        WebSession.objects.create(
            visitor=visitor, lead=lead, started_at=acquired, last_seen_at=acquired,
            landing_path="/", consent_state="ESSENTIAL", utm_campaign="cohorte",
            utm_source="instagram", utm_medium="paid_social", utm_content=content,
        )
    Sale.objects.create(
        lead=lead_a, offering=catalog["offering"], listing=catalog["listing"],
        sale_price=1_000_000, closed_at=acquired_a + timedelta(days=100), created_by=owner,
    )
    Sale.objects.create(
        lead=lead_b, offering=catalog["offering"], listing=catalog["listing"],
        sale_price=1_000_000, closed_at=acquired_b + timedelta(days=80), created_by=owner,
    )

    response = admin_client.get(
        "/api/v1/admin/bi/marketing/?period=custom&start=2026-08-01&end=2026-08-31&horizon=90"
    )
    assert response.status_code == 200, response.data
    campaign = next(row for row in response.data["campaigns"] if row["utm_campaign"] == "cohorte")
    assert campaign["leads"] == 2
    assert campaign["closed_sales"] == 1
    creatives = {row["utm_content"]: row for row in response.data["creatives"]}
    assert creatives["content_a"]["closed_sales"] == 0
    assert creatives["content_b"]["closed_sales"] == 1


@pytest.mark.django_db
def test_campaign_with_spend_and_zero_sessions_is_visible_without_fake_costs(admin_client, owner):
    campaign = MarketingCampaign.objects.create(
        name="Facebook Chalco Agosto", utm_campaign="chalco_agosto", channel="Social",
        start_date=datetime(2026, 8, 1).date(), created_by=owner, updated_by=owner,
    )
    MarketingSpend.objects.create(campaign=campaign, date=datetime(2026, 8, 10).date(), amount=5000)
    response = admin_client.get(
        "/api/v1/admin/bi/marketing/?period=custom&start=2026-08-01&end=2026-08-31&horizon=90"
    )
    assert response.status_code == 200, response.data
    row = next(item for item in response.data["campaigns"] if item["utm_campaign"] == "chalco_agosto")
    assert row["sessions"] == row["leads"] == row["closed_sales"] == 0
    assert row["spend"] == 5000
    assert row["cost_per_lead"] is None
    assert row["cost_per_inquiry"] is None
    assert row["cost_per_completed_visit"] is None
    assert row["cost_per_sale"] is None
