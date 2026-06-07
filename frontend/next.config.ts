import type { NextConfig } from "next"

/**
 * Single-server dev: open http://127.0.0.1:3000 (frontend) → proxy → http://127.0.0.1:9876 (backend).
 * TSOC_DEV_ORIGIN defaults to 127.0.0.1; comma-separate hostnames/IPs you open in the browser.
 */
const extraDevOrigins = (process.env.TSOC_DEV_ORIGIN || "127.0.0.1")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean)

const LOCAL_DEV_ORIGINS = [...new Set(["127.0.0.1", "localhost", ...extraDevOrigins])]

const nextConfig: NextConfig = {
  allowedDevOrigins: LOCAL_DEV_ORIGINS,
  async redirects() {
    return [
      {
        source: "/index",
        destination: "/",
        permanent: false,
      },
    ]
  },
}

export default nextConfig
