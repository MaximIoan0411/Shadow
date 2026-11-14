/**
 * `npm run app:dev` — aplicația de desktop peste serverul Next de dezvoltare (cu reîncărcare la salvare).
 * Pornește `next dev` dacă nu rulează deja pe portul 3000, așteaptă să răspundă, apoi deschide Electron.
 */
const { spawn } = require("node:child_process");
const http = require("node:http");

const DEV_URL = "http://localhost:3000";
const POLL_MS = 400;
const TIMEOUT_MS = 90_000;

const isUp = () =>
  new Promise((resolve) => {
    const request = http.get(`${DEV_URL}/login`, { timeout: 1000 }, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.on("timeout", () => request.destroy());
    request.on("error", () => resolve(false));
  });

async function waitUntilUp(startedAt) {
  if (await isUp()) return;
  if (Date.now() - startedAt > TIMEOUT_MS) throw new Error("The Next server did not start within 90 seconds.");
  await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  await waitUntilUp(startedAt);
}

async function main() {
  const alreadyUp = await isUp();
  const next = alreadyUp ? null : spawn(process.execPath, [require.resolve("next/dist/bin/next"), "dev", "-p", "3000"], { stdio: "inherit" });
  await waitUntilUp(Date.now());
  const electron = spawn(require("electron"), ["."], { stdio: "inherit", env: { ...process.env, SHADOW_DEV_URL: DEV_URL } });
  electron.on("exit", (code) => {
    next?.kill();
    process.exit(code ?? 0);
  });
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
