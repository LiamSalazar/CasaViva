"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { apiFetch } from "@/services/api";
import { ensureAnalyticsIdentity, getAnalyticsIdentity } from "@/services/analytics-session";

export async function trackEvent(eventName: string, properties: Record<string, unknown> = {}, relations: Record<string, string | undefined> = {}) {
  if (typeof window === "undefined") return;
  const { visitorId, sessionId } = getAnalyticsIdentity();
  if (!visitorId || !sessionId) return;
  await apiFetch("/api/v1/public/analytics/events/", {
    method: "POST",
    body: JSON.stringify({
      occurred_at: new Date().toISOString(),
      event_name: eventName,
      schema_version: 1,
      visitor_id: visitorId,
      session_id: sessionId,
      page_path: `${location.pathname}${location.search}`,
      properties,
      ...relations,
    }),
  });
}

export function AnalyticsProvider() {
  const pathname = usePathname();
  const search = useSearchParams();
  useEffect(() => {
    if (pathname.startsWith("/administracion") || pathname.startsWith("/admin") || pathname.startsWith("/preview")) return;
    let cancelled = false;
    const track = async () => {
      let identity = getAnalyticsIdentity();
      if (!identity.sessionId) {
        const params = new URLSearchParams(window.location.search);
        identity = await ensureAnalyticsIdentity((visitorId) =>
          apiFetch<{ visitor_id: string; session_id: string }>("/api/v1/public/analytics/session/", {
            method: "POST",
            body: JSON.stringify({ visitor_id: visitorId, landing_path: `${pathname}${search.size ? `?${search}` : ""}`, consent_state: "ESSENTIAL", utm_source: params.get("utm_source"), utm_medium: params.get("utm_medium"), utm_campaign: params.get("utm_campaign"), utm_content: params.get("utm_content"), utm_term: params.get("utm_term"), referrer_domain: document.referrer ? new URL(document.referrer).hostname : null, device_category: window.innerWidth < 768 ? "mobile" : window.innerWidth < 1100 ? "tablet" : "desktop" }),
          }),
        );
      }
      const { visitorId, sessionId } = identity;
      if (!cancelled && visitorId && sessionId) await apiFetch("/api/v1/public/analytics/events/", { method: "POST", body: JSON.stringify({ occurred_at: new Date().toISOString(), event_name: "page_viewed", schema_version: 1, visitor_id: visitorId, session_id: sessionId, page_path: `${pathname}${search.size ? `?${search}` : ""}`, properties: {} }) });
    };
    void track().catch(() => undefined);
    return () => { cancelled = true; };
  }, [pathname, search]);
  return null;
}
