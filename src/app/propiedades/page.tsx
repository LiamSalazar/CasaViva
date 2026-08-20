import { Suspense } from "react";
import { PropertiesPage } from "@/components/search-pages";
export const metadata = { title: "Propiedades en venta" };
export default function Page() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh" }} />}>
      <PropertiesPage />
    </Suspense>
  );
}
