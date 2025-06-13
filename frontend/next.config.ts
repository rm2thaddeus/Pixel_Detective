import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Temporarily disable package optimization to fix import issues
  // experimental: {
  //   optimizePackageImports: ["@chakra-ui/react"],
  // },
};

export default nextConfig;
