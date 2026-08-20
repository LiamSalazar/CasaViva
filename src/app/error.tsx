"use client";
import { Footer, PublicHeader } from "@/components/ui";
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) { return <><PublicHeader /><main className="narrow section"><span className="eyebrow">CasaViva</span><h1 style={{ fontSize: "clamp(3rem,6vw,6rem)" }}>No pudimos mostrar esta página</h1><p className="muted">Intenta nuevamente. Si el problema continúa, vuelve al inicio.</p><button className="button" onClick={reset}>Intentar de nuevo</button></main><Footer /></>; }
