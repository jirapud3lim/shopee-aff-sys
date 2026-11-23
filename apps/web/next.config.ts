import type { NextConfig } from "next";

const config: NextConfig = {
  agentRules: false,
  experimental: { proxyClientMaxBodySize: "66mb" },
  async rewrites() {
    const backend = process.env.STUDIO_API_ORIGIN ?? "http://127.0.0.1:8001";
    return [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }];
  },
};

export default config;
