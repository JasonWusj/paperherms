/** @type {import('next').NextConfig} */
const internalApiBaseUrl = process.env.INTERNAL_API_BASE_URL ?? "http://127.0.0.1:8010/api";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiBaseUrl}/:path*`
      }
    ];
  }
};

export default nextConfig;
