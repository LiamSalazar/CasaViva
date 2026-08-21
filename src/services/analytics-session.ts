export const ANALYTICS_VISITOR_KEY = "casaviva-visitor-id";
export const ANALYTICS_SESSION_KEY = "casaviva-session-id";

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
  return {
    visitorId: localStorage.getItem(ANALYTICS_VISITOR_KEY) || undefined,
    sessionId: sessionStorage.getItem(ANALYTICS_SESSION_KEY) || undefined,
  };
}

export function storeAnalyticsIdentity(visitorId: string, sessionId: string) {
  localStorage.setItem(ANALYTICS_VISITOR_KEY, visitorId);
  sessionStorage.setItem(ANALYTICS_SESSION_KEY, sessionId);
}

/**
 * Reuses the same in-flight request when React mounts the provider twice in
 * development strict mode. This keeps one browser tab mapped to one web
 * session instead of creating two attribution records concurrently.
 */
export function ensureAnalyticsIdentity(
  createSession: (visitorId?: string) => Promise<CreatedAnalyticsIdentity>,
): Promise<AnalyticsIdentity> {
  const existing = getAnalyticsIdentity();
  if (existing.visitorId && existing.sessionId) return Promise.resolve(existing);
  if (pendingSession) return pendingSession;

  pendingSession = createSession(existing.visitorId)
    .then((created) => {
      storeAnalyticsIdentity(created.visitor_id, created.session_id);
      return { visitorId: created.visitor_id, sessionId: created.session_id };
    })
    .finally(() => {
      pendingSession = undefined;
    });
  return pendingSession;
}
