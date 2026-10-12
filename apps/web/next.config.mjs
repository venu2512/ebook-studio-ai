/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // The shared workspace package ships TypeScript source.
  transpilePackages: ["@ebook/shared"],
  eslint: {
    // Lint is run explicitly in CI (`pnpm lint`); keep builds fast and robust.
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost" },
      { protocol: "http", hostname: "127.0.0.1" },
      { protocol: "http", hostname: "minio" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
