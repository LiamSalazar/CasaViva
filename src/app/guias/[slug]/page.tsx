import type { Metadata } from "next";
import { GuideDetailPage } from "@/components/editorial-pages";
import { serverApi } from "@/services/server-api";
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const g = await serverApi<Record<string, any>>(`/api/v1/public/guides/${slug}/`);
  return {
    title: g ? `${g.title} | Guías CasaViva` : "Guía CasaViva",
    description: g?.excerpt,
  };
}
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <GuideDetailPage slug={slug} />;
}
