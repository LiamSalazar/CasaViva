"use client";

import { usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/services/api";
import { ensureAnalyticsIdentity, touchAnalyticsSession, type AcquisitionAttribution } from "@/services/analytics-session";

function currentAttribution(): AcquisitionAttribution {
  const params = new URLSearchParams(window.location.search);
  return { utm_source: params.get("utm_source"), utm_medium: params.get("utm_medium"), utm_campaign: params.get("utm_campaign"), utm_content: params.get("utm_content"), utm_term: params.get("utm_term") };
}

const ANALYTICS_PREFERENCE_KEY = "casaviva-analytics-preference";
type AnalyticsPreference = "understood" | "limited";
function analyticsPreference(): AnalyticsPreference | null {
  if (typeof window === "undefined") return null;
  const value = localStorage.getItem(ANALYTICS_PREFERENCE_KEY);
  return value === "limited" || value === "understood" ? value : null;
}

export function ensureCurrentAnalyticsIdentity() {
  if (analyticsPreference() !== "understood") return Promise.resolve({ visitorId: undefined, sessionId: undefined });
  const attribution = currentAttribution();
  return ensureAnalyticsIdentity((visitorId) =>
    apiFetch<{ visitor_id: string; session_id: string }>("/api/v1/public/analytics/session/", {
      method: "POST",
      body: JSON.stringify({ visitor_id: visitorId, landing_path: `${location.pathname}${location.search}`, consent_state: "SESSION_ANALYTICS", ...attribution, referrer_domain: document.referrer ? new URL(document.referrer).hostname : null, device_category: window.innerWidth < 768 ? "mobile" : window.innerWidth < 1100 ? "tablet" : "desktop" }),
    }), attribution,
  );
}

export async function trackEvent(eventName: string, properties: Record<string, unknown> = {}, relations: Record<string, string | undefined> = {}) {
  if (typeof window === "undefined") return;
  if (analyticsPreference() !== "understood") return;
  const { visitorId, sessionId } = await ensureCurrentAnalyticsIdentity();
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
  touchAnalyticsSession();
}

export function AnalyticsProvider() {
  const pathname = usePathname();
  const search = useSearchParams();
  const [preference, setPreference] = useState<AnalyticsPreference | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => { setPreference(analyticsPreference()); setReady(true); }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (pathname.startsWith("/administracion") || pathname.startsWith("/admin") || pathname.startsWith("/preview")) return;
    if (preference !== "understood") return;
    let cancelled = false;
    const track = async () => {
      const identity = await ensureCurrentAnalyticsIdentity();
      const { visitorId, sessionId } = identity;
      if (!cancelled && visitorId && sessionId) {
        await apiFetch("/api/v1/public/analytics/events/", { method: "POST", body: JSON.stringify({ occurred_at: new Date().toISOString(), event_name: "page_viewed", schema_version: 1, visitor_id: visitorId, session_id: sessionId, page_path: `${pathname}${search.size ? `?${search}` : ""}`, properties: {} }) });
        touchAnalyticsSession();
      }
    };
    void track().catch(() => undefined);
    return () => { cancelled = true; };
  }, [pathname, search, preference]);
  if (!ready || preference || pathname.startsWith("/administracion") || pathname.startsWith("/admin") || pathname.startsWith("/preview")) return null;
  const choose = (value: AnalyticsPreference) => { localStorage.setItem(ANALYTICS_PREFERENCE_KEY, value); setPreference(value); };
  return <aside className="analytics-notice" aria-label="Preferencias de analítica">
    <p>CasaViva utiliza almacenamiento técnico de sesión y analítica propia para operar y entender el uso del sitio. No utilizamos píxeles publicitarios de terceros en esta etapa.</p>
    <div><button type="button" onClick={() => choose("understood")}>Entendido</button><button type="button" onClick={() => choose("limited")}>Limitar analítica</button><Link href="/aviso-de-privacidad">Más información</Link></div>
  </aside>;
}
