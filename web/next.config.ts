import type { NextConfig } from "next";

// Static export: the site is plain files in `out/`. There is no Next.js server, so
// response headers (CSP etc.) must be configured at the hosting layer, not here.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true, // /scan/ -> out/scan/index.html, works with any static file server
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
