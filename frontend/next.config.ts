import type { NextConfig } from "next";

/**
 * Două moduri de a rula frontend-ul:
 *   - `npm run dev` / `npm run start`: server Next; cererile `/api/*` și `/health` sunt duse la backend de regula
 *     `rewrites` de mai jos (SHADOW_API_URL, implicit http://127.0.0.1:8000);
 *   - `npm run build:app` (SHADOW_EXPORT=1): export static în `out/`, pentru aplicația Electron. Acolo proxy-ul
 *     spre backend e în electron/main.cjs, iar `rewrites` nu se folosește.
 */
const API_URL = process.env.SHADOW_API_URL ?? "http://127.0.0.1:8000";
const isExport = process.env.SHADOW_EXPORT === "1";

const config: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  // gzip-ul serverului de dezvoltare ar ține în tampon fluxul de evenimente (SSE)
  compress: false,
  images: { unoptimized: true },
  ...(isExport
    ? { output: "export" as const }
    : {
        // alt folder decât cel al exportului (`.next`), ca `npm run dev` și `npm run app` să poată rula în același timp
        distDir: ".next-dev",
        async rewrites() {
          return [
            { source: "/api/:path*", destination: `${API_URL}/api/:path*` },
            { source: "/health", destination: `${API_URL}/health` },
          ];
        },
      }),
};

export default config;
