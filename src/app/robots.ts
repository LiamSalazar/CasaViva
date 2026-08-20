import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const origin = process.env.NEXT_PUBLIC_SITE_URL || "https://casaviva.mx";
  return { rules: [{ userAgent: "*", allow: "/", disallow: ["/administracion/", "/admin/", "/preview/", "/api/"] }], sitemap: `${origin}/sitemap.xml` };
}
