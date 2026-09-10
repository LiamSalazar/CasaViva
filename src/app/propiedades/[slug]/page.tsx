import type { Metadata } from "next";
import { PropertyDetailPage } from "@/components/search-pages";
import { serverApi } from "@/services/server-api";
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const p = await serverApi<Record<string, any>>(`/api/v1/public/listings/${slug}/`);
  return {
    title: p ? `${p.title}${p.municipality ? ` en ${p.municipality}` : ""}` : "Propiedad",
    description: p?.shortDescription || undefined,
    openGraph: p?.heroImage ? { images: [p.heroImage] } : undefined,
    alternates: { canonical: `/propiedades/${slug}` },
  };
}
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <PropertyDetailPage slug={slug} />;
}
