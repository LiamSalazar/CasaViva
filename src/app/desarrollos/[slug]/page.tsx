import type { Metadata } from "next";
import { DevelopmentDetailPage } from "@/components/editorial-pages";
import { serverApi } from "@/services/server-api";
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const d = await serverApi<Record<string, any>>(`/api/v1/public/developments/${slug}/`);
  return {
    title: d ? `${d.name} en ${d.municipality}` : "Desarrollo",
    description: d?.shortDescription,
  };
}
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <DevelopmentDetailPage slug={slug} />;
}
