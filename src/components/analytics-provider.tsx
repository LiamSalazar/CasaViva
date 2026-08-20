"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { apiFetch } from "@/services/api";

const VISITOR_KEY = "casaviva-visitor-id";
const SESSION_KEY = "casaviva-session-id";

export async function trackEvent(eventName: string, properties: Record<string, unknown> = {}, relations: Record<string, string | undefined> = {}) {
  if (typeof window === "undefined") return;
  const visitorId = localStorage.getItem(VISITOR_KEY);
  const sessionId = sessionStorage.getItem(SESSION_KEY);
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
      let visitorId = localStorage.getItem(VISITOR_KEY);
      let sessionId = sessionStorage.getItem(SESSION_KEY);
      if (!sessionId) {
        const params = new URLSearchParams(window.location.search);
        const created = await apiFetch<{ visitor_id: string; session_id: string }>("/api/v1/public/analytics/session/", { method: "POST", body: JSON.stringify({ visitor_id: visitorId, landing_path: `${pathname}${search.size ? `?${search}` : ""}`, consent_state: "ESSENTIAL", utm_source: params.get("utm_source"), utm_medium: params.get("utm_medium"), utm_campaign: params.get("utm_campaign"), utm_content: params.get("utm_content"), utm_term: params.get("utm_term"), referrer_domain: document.referrer ? new URL(document.referrer).hostname : null, device_category: window.innerWidth < 768 ? "mobile" : window.innerWidth < 1100 ? "tablet" : "desktop" }) });
        visitorId = created.visitor_id; sessionId = created.session_id;
        localStorage.setItem(VISITOR_KEY, visitorId); sessionStorage.setItem(SESSION_KEY, sessionId);
      }
      if (!cancelled && visitorId && sessionId) await apiFetch("/api/v1/public/analytics/events/", { method: "POST", body: JSON.stringify({ occurred_at: new Date().toISOString(), event_name: "page_viewed", schema_version: 1, visitor_id: visitorId, session_id: sessionId, page_path: `${pathname}${search.size ? `?${search}` : ""}`, properties: {} }) });
    };
    void track().catch(() => undefined);
    return () => { cancelled = true; };
  }, [pathname, search]);
  return null;
}
