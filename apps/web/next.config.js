/** @type {import('next').NextConfig} */
const API_PROXY_TARGET = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    missingSuspenseWithCSRBailout: false,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_PROXY_TARGET}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
