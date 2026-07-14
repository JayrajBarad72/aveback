"""
GA4 Analytics Agent — pulls real visitor data from Google Analytics 4
Property: aventrixtechnologies.com (ID: 222597880)
Credentials: GA_SERVICE_ACCOUNT_JSON env var (JSON string)
"""
import os
import json
from datetime import datetime, timedelta


GA4_PROPERTY_ID = "222597880"


def get_ga_client():
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.oauth2 import service_account

    creds_json = os.environ.get("GA_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        raise ValueError("GA_SERVICE_ACCOUNT_JSON env var not set")

    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    return BetaAnalyticsDataClient(credentials=creds)


def get_website_analytics(days: int = 7) -> dict:
    """Pull key GA4 metrics for the last N days."""
    try:
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Dimension, Metric, DateRange, OrderBy
        )
        client = get_ga_client()
        date_range = DateRange(start_date=f"{days}daysAgo", end_date="today")

        # --- Overview metrics ---
        overview = client.run_report(RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[date_range],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="newUsers"),
                Metric(name="sessions"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="screenPageViews"),
            ]
        ))
        ov = overview.rows[0].metric_values if overview.rows else []
        summary = {
            "active_users":   int(ov[0].value) if ov else 0,
            "new_users":      int(ov[1].value) if ov else 0,
            "sessions":       int(ov[2].value) if ov else 0,
            "avg_session_sec": round(float(ov[3].value)) if ov else 0,
            "bounce_rate":    round(float(ov[4].value) * 100, 1) if ov else 0,
            "page_views":     int(ov[5].value) if ov else 0,
        }

        # --- Top pages ---
        pages_resp = client.run_report(RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[date_range],
            dimensions=[Dimension(name="pageTitle")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="activeUsers"),
                Metric(name="bounceRate"),
            ],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
            limit=8
        ))
        top_pages = []
        for row in pages_resp.rows:
            top_pages.append({
                "page":        row.dimension_values[0].value,
                "views":       int(row.metric_values[0].value),
                "users":       int(row.metric_values[1].value),
                "bounce_rate": round(float(row.metric_values[2].value) * 100, 1),
            })

        # --- Traffic sources ---
        sources_resp = client.run_report(RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[date_range],
            dimensions=[Dimension(name="sessionSource"), Dimension(name="sessionMedium")],
            metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=8
        ))
        traffic_sources = []
        for row in sources_resp.rows:
            traffic_sources.append({
                "source":  row.dimension_values[0].value,
                "medium":  row.dimension_values[1].value,
                "sessions": int(row.metric_values[0].value),
                "users":   int(row.metric_values[1].value),
            })

        # --- Countries ---
        geo_resp = client.run_report(RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[date_range],
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="activeUsers")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="activeUsers"), desc=True)],
            limit=8
        ))
        countries = []
        for row in geo_resp.rows:
            countries.append({
                "country": row.dimension_values[0].value,
                "users":   int(row.metric_values[0].value),
            })

        # --- Daily trend (last 7 days) ---
        trend_resp = client.run_report(RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[date_range],
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="activeUsers"), Metric(name="sessions")],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        ))
        daily_trend = []
        for row in trend_resp.rows:
            d = row.dimension_values[0].value
            daily_trend.append({
                "date":     f"{d[:4]}-{d[4:6]}-{d[6:]}",
                "users":    int(row.metric_values[0].value),
                "sessions": int(row.metric_values[1].value),
            })

        return {
            "success":        True,
            "period_days":    days,
            "fetched_at":     datetime.utcnow().isoformat(),
            "summary":        summary,
            "top_pages":      top_pages,
            "traffic_sources": traffic_sources,
            "countries":      countries,
            "daily_trend":    daily_trend,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_realtime_users() -> dict:
    """Get currently active users on the site right now."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import RunRealtimeReportRequest, Dimension, Metric
        client = get_ga_client()
        resp = client.run_realtime_report(RunRealtimeReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="activeUsers")],
            limit=10
        ))
        active = []
        total = 0
        for row in resp.rows:
            u = int(row.metric_values[0].value)
            active.append({"country": row.dimension_values[0].value, "users": u})
            total += u
        return {"success": True, "total_active_now": total, "by_country": active}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_analytics_summary_for_alex(days: int = 7) -> str:
    """Plain-English summary Alex can read and act on."""
    data = get_website_analytics(days)
    if not data.get("success"):
        return f"GA4 fetch failed: {data.get('error','unknown')}"

    s = data["summary"]
    pages = data["top_pages"]
    sources = data["traffic_sources"]
    countries = data["countries"]

    top_page = pages[0]["page"] if pages else "N/A"
    top_src = f"{sources[0]['source']}/{sources[0]['medium']}" if sources else "direct"
    top_country = countries[0]["country"] if countries else "N/A"
    organic = next((x for x in sources if "organic" in x.get("medium", "")), None)
    organic_sessions = organic["sessions"] if organic else 0

    pricing_visits = next((p["users"] for p in pages if "Pricing" in p.get("page", "")), 0)
    contact_visits = next((p["users"] for p in pages if "Contact" in p.get("page", "")), 0)

    summary = f"""WEBSITE ANALYTICS — Last {days} days
Active users: {s['active_users']} ({s['new_users']} new)
Sessions: {s['sessions']} | Avg duration: {s['avg_session_sec']}s | Bounce: {s['bounce_rate']}%
Top page: {top_page} | Top traffic source: {top_src}
Top country: {top_country}
Google organic sessions: {organic_sessions}

HIGH-INTENT SIGNALS:
- Pricing page visitors: {pricing_visits} (hot leads)
- Contact page visitors: {contact_visits} (very hot)

COUNTRIES: {', '.join([f"{c['country']} ({c['users']})" for c in countries[:5]])}

ACTION INSIGHT: {'Pricing page has ' + str(pricing_visits) + ' visitors — check if any match outreach leads and prioritize follow-up.' if pricing_visits > 0 else 'No pricing page visits yet — check if CTA buttons are working.'}"""

    return summary
