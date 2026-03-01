/** @type {import('next').NextConfig} */
const API_PROXY_TARGET =
  process.env.API_PROXY_TARGET ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    missingSuspenseWithCSRBailout: false,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path((?!auth/|me$|user/sync$).*)",
        destination: `${API_PROXY_TARGET}/api/:path`,
      },
    ];
  },
};

module.exports = nextConfig;
