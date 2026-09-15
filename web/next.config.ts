import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dev: allow access via 127.0.0.1 as well as localhost.
  allowedDevOrigins: ["127.0.0.1"],
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },
};

export default nextConfig;
