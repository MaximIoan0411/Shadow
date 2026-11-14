/**
 * Construiește frontend-ul pentru aplicația de desktop: export static în `out/`.
 * E un script Node (nu `SHADOW_EXPORT=1 next build`) ca să meargă la fel pe Windows, macOS și Linux.
 */
const { spawnSync } = require("node:child_process");

const result = spawnSync(process.execPath, [require.resolve("next/dist/bin/next"), "build"], {
  stdio: "inherit",
  env: { ...process.env, SHADOW_EXPORT: "1" },
});
process.exit(result.status ?? 1);
