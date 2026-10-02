import type { NextConfig } from "next";

// Production: static files served by FastAPI. Development: proxy /api to the backend on :8000.
const nextConfig: NextConfig =
  process.env.NODE_ENV === "development"
    ? {
        async rewrites() {
          return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
        },
      }
    : { output: "export", trailingSlash: true, images: { unoptimized: true } };

export default nextConfig;
