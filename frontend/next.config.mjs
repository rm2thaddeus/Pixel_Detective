/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8002',
        pathname: '/api/v1/images/**',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/dev-graph/:path*',
        destination: 'http://localhost:8080/api/v1/dev-graph/:path*',
      },
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8002/api/v1/:path*',
      },
    ]
  },
};

export default nextConfig; 