import type { MetadataRoute } from "next";
import { serverApi } from "@/services/server-api";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = process.env.NEXT_PUBLIC_SITE_URL || "https://casaviva.mx";
  const [listings, developments, guides] = await Promise.all([
    serverApi<{ results: Array<{ slug: string; updatedAt: string }> }>("/api/v1/public/listings/?page_size=100"),
    serverApi<{ results: Array<{ slug: string; updated_at?: string }> }>("/api/v1/public/developments/"),
    serverApi<{ results: Array<{ slug: string; createdAt: string }> }>("/api/v1/public/guides/?page_size=100"),
  ]);
  return [
    { url: origin, changeFrequency: "daily", priority: 1 },
    { url: `${origin}/propiedades`, changeFrequency: "daily", priority: 0.9 },
    { url: `${origin}/desarrollos`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${origin}/guias`, changeFrequency: "weekly", priority: 0.7 },
    ...(listings?.results || []).map((x) => ({ url: `${origin}/propiedades/${x.slug}`, lastModified: x.updatedAt, changeFrequency: "weekly" as const, priority: 0.8 })),
    ...(developments?.results || []).map((x) => ({ url: `${origin}/desarrollos/${x.slug}`, lastModified: x.updated_at, changeFrequency: "weekly" as const, priority: 0.7 })),
    ...(guides?.results || []).map((x) => ({ url: `${origin}/guias/${x.slug}`, lastModified: x.createdAt, changeFrequency: "monthly" as const, priority: 0.6 })),
  ];
}
