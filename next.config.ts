import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Django/DRF distinguishes collection URLs with a trailing slash. Preserve it
  // so POST bodies are never converted into GET requests by a redirect.
  skipTrailingSlashRedirect: true,
  images: {
    remotePatterns: [{ protocol: "https", hostname: "images.unsplash.com" }],
  },
  async rewrites() {
    const backend = process.env.DJANGO_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/media/:path*", destination: `${backend}/media/:path*` },
    ];
  },
};

export default nextConfig;
