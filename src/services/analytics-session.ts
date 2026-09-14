export const LEGACY_ANALYTICS_VISITOR_KEY = "casaviva-visitor-id";
export const ANALYTICS_VISITOR_KEY = "casaviva-session-visitor-id";
export const ANALYTICS_SESSION_KEY = "casaviva-session-id";
export const ANALYTICS_LAST_ACTIVITY_KEY = "casaviva-session-last-activity";
export const ANALYTICS_ATTRIBUTION_KEY = "casaviva-session-attribution";
export const ANALYTICS_SESSION_TIMEOUT_MS = 30 * 60 * 1000;

export interface AcquisitionAttribution {
  utm_source?: string | null;
  utm_medium?: string | null;
  utm_campaign?: string | null;
  utm_content?: string | null;
  utm_term?: string | null;
}

export interface AnalyticsIdentity {
  visitorId?: string;
  sessionId?: string;
}

interface CreatedAnalyticsIdentity {
  visitor_id: string;
  session_id: string;
}

let pendingSession: Promise<AnalyticsIdentity> | undefined;

export function getAnalyticsIdentity(): AnalyticsIdentity {
  if (typeof window === "undefined") return { visitorId: undefined, sessionId: undefined };
  const lastActivity = Number(sessionStorage.getItem(ANALYTICS_LAST_ACTIVITY_KEY) || 0);
  if (lastActivity && Date.now() - lastActivity > ANALYTICS_SESSION_TIMEOUT_MS) {
    sessionStorage.removeItem(ANALYTICS_VISITOR_KEY);
    sessionStorage.removeItem(ANALYTICS_SESSION_KEY);
    sessionStorage.removeItem(ANALYTICS_LAST_ACTIVITY_KEY);
    sessionStorage.removeItem(ANALYTICS_ATTRIBUTION_KEY);
  }
  return {
    visitorId: sessionStorage.getItem(ANALYTICS_VISITOR_KEY) || undefined,
    sessionId: sessionStorage.getItem(ANALYTICS_SESSION_KEY) || undefined,
  };
}

export function storeAnalyticsIdentity(visitorId: string, sessionId: string, attribution: AcquisitionAttribution = {}) {
  localStorage.removeItem(LEGACY_ANALYTICS_VISITOR_KEY);
  sessionStorage.setItem(ANALYTICS_VISITOR_KEY, visitorId);
  sessionStorage.setItem(ANALYTICS_SESSION_KEY, sessionId);
  sessionStorage.setItem(ANALYTICS_LAST_ACTIVITY_KEY, String(Date.now()));
  sessionStorage.setItem(ANALYTICS_ATTRIBUTION_KEY, JSON.stringify(attribution));
}

export function touchAnalyticsSession() {
  if (typeof window !== "undefined" && sessionStorage.getItem(ANALYTICS_SESSION_KEY))
    sessionStorage.setItem(ANALYTICS_LAST_ACTIVITY_KEY, String(Date.now()));
}

function materialAttributionChanged(next: AcquisitionAttribution) {
  const hasNewAcquisition = Boolean(next.utm_source || next.utm_medium || next.utm_campaign);
  if (!hasNewAcquisition) return false;
  let current: AcquisitionAttribution = {};
  try { current = JSON.parse(sessionStorage.getItem(ANALYTICS_ATTRIBUTION_KEY) || "{}"); } catch { current = {}; }
  return (["utm_source", "utm_medium", "utm_campaign"] as const).some(
    (key) => (current[key] || null) !== (next[key] || null),
  );
}

/**
 * Reuses the same in-flight request when React mounts the provider twice in
 * development strict mode. This keeps one browser tab mapped to one web
 * session instead of creating two attribution records concurrently.
 */
export function ensureAnalyticsIdentity(
  createSession: (visitorId?: string) => Promise<CreatedAnalyticsIdentity>,
  attribution: AcquisitionAttribution = {},
): Promise<AnalyticsIdentity> {
  let existing = getAnalyticsIdentity();
  if (existing.sessionId && materialAttributionChanged(attribution)) {
    sessionStorage.removeItem(ANALYTICS_SESSION_KEY);
    sessionStorage.removeItem(ANALYTICS_LAST_ACTIVITY_KEY);
    existing = { visitorId: existing.visitorId };
  }
  if (existing.visitorId && existing.sessionId) return Promise.resolve(existing);
  if (pendingSession) return pendingSession;

  pendingSession = createSession(existing.visitorId)
    .then((created) => {
      storeAnalyticsIdentity(created.visitor_id, created.session_id, attribution);
      return { visitorId: created.visitor_id, sessionId: created.session_id };
    })
    .finally(() => {
      pendingSession = undefined;
    });
  return pendingSession;
}
