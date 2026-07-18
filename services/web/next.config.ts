import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static files for Raspberry Pi (nginx / python -m http.server / caddy).
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
