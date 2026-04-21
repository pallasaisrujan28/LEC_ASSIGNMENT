/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/agent/:path*',
        destination: 'http://localhost:8000/agent/:path*',
      },
      {
        source: '/health',
        destination: 'http://localhost:8000/health',
      },
    ];
  },
};

export default nextConfig;
