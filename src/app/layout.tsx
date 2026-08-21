import type { Metadata } from "next";
import { Suspense } from "react";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import { ToastProvider } from "@/components/ui";
import { DataProvider } from "@/components/data-provider";
import { AnalyticsProvider } from "@/components/analytics-provider";

export const metadata: Metadata = {
  title: { default: "CasaViva — Encuentra hogar", template: "%s | CasaViva" },
  description:
    "Propiedades y desarrollos en México presentados con claridad y cuidado.",
  openGraph: {
    title: "CasaViva",
    description: "Una forma más clara de encontrar hogar.",
    type: "website",
  },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" data-scroll-behavior="smooth">
      <body>
        <DataProvider><Suspense fallback={null}><AnalyticsProvider /></Suspense><ToastProvider>{children}</ToastProvider></DataProvider>
      </body>
    </html>
  );
}
