"use client";

import Script from "next/script";
import { useEffect, useId, useRef, useState } from "react";

declare global {
  interface Window {
    turnstile?: {
      render: (target: string | HTMLElement, options: Record<string, unknown>) => string;
      reset: (widgetId?: string) => void;
      remove: (widgetId: string) => void;
    };
  }
}

const enabled = process.env.NEXT_PUBLIC_ANTIBOT_ENABLED === "true";
const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";
const testToken = process.env.NEXT_PUBLIC_TURNSTILE_TEST_TOKEN || "";

export function antibotIsEnabled() {
  return enabled;
}

export function TurnstileWidget({ onToken, resetSignal }: { onToken: (token: string) => void; resetSignal: number }) {
  const reactId = useId();
  const elementId = `turnstile-${reactId.replaceAll(":", "")}`;
  const widgetId = useRef<string | undefined>(undefined);
  const [scriptReady, setScriptReady] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    if (testToken) {
      onToken(testToken);
      return;
    }
    if (!scriptReady || !window.turnstile || widgetId.current) return;
    widgetId.current = window.turnstile.render(`#${elementId}`, {
      sitekey: siteKey,
      callback: (token: string) => onToken(token),
      "expired-callback": () => onToken(""),
      "error-callback": () => onToken(""),
    });
    return () => {
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = undefined;
    };
  }, [elementId, onToken, scriptReady]);

  useEffect(() => {
    if (!enabled || resetSignal === 0) return;
    onToken(testToken);
    if (!testToken && widgetId.current && window.turnstile) window.turnstile.reset(widgetId.current);
  }, [onToken, resetSignal]);

  if (!enabled) return null;
  if (!siteKey && !testToken) return <p className="form-error">La verificación antibot no está configurada.</p>;
  if (testToken) return <><div id={elementId} data-testid="turnstile-widget" style={{ minHeight: 1 }} /><p className="muted">Verificación de seguridad de prueba.</p></>;
  return <><Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" strategy="afterInteractive" onLoad={() => setScriptReady(true)} /><div id={elementId} data-testid="turnstile-widget" /><p className="muted">Verificación de seguridad requerida.</p></>;
}
