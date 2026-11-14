/**
 * SHADOW — aplicația de desktop (Electron).
 *
 * Ce face procesul principal:
 *   1. servește frontend-ul exportat static (`out/`) de pe un server local, pe 127.0.0.1;
 *   2. duce cererile `/api/*` și `/health` la backend (inclusiv fluxul de evenimente), deci frontend-ul lucrează
 *      pe aceeași origine și nu depinde de CORS;
 *   3. dacă backend-ul nu răspunde și există folderul `../backend`, îl pornește cu `uv` și îl oprește la ieșire.
 *
 * Variabile de mediu:
 *   SHADOW_API_URL       adresa backend-ului (implicit http://127.0.0.1:8000)
 *   SHADOW_DEV_URL       încarcă frontend-ul de la serverul Next de dezvoltare (ex. http://localhost:3000)
 *   SHADOW_BACKEND_DIR   folderul backend-ului (implicit ../backend, lângă frontend/)
 *   SHADOW_NO_BACKEND=1  nu porni backend-ul; doar conectează-te la el
 */
const { app, BrowserWindow, Menu, ipcMain, nativeTheme, shell } = require("electron");
const { spawn, execFile } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const BACKEND_URL = new URL(process.env.SHADOW_API_URL ?? "http://127.0.0.1:8000");
const DEV_URL = process.env.SHADOW_DEV_URL ?? null;
const OUT_DIR = path.join(__dirname, "..", "out");
const BACKEND_DIR = process.env.SHADOW_BACKEND_DIR ?? path.join(__dirname, "..", "..", "backend");
const BACKGROUND = "#0b0a0f";
const HEALTH_TIMEOUT_MS = 1500;
const BACKEND_BOOT_TIMEOUT_MS = 120_000;
const BACKEND_POLL_MS = 500;
const LOG_LINES_KEPT = 12;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
};

// ---------------------------------------------------------------- backend

/** Starea backend-ului, așa cum o vede ecranul de autentificare prin `window.shadowDesktop.backendStatus()`. */
const backend = {
  state: "disabled", // external | starting | running | failed | disabled
  detail: "",
  process: null,
  log: [],
};

/**
 * Ce răspunde pe portul backend-ului: "shadow" (backend-ul nostru), "other" (alt program, ex. `php artisan serve`
 * sau alt server de dezvoltare pe 8000) sau "none" (nimic).
 */
function probeBackend() {
  return new Promise((resolve) => {
    const request = http.get(new URL("/health", BACKEND_URL), { timeout: HEALTH_TIMEOUT_MS }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => {
        try {
          const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
          resolve(response.statusCode === 200 && body.ok === true && typeof body.version === "string" ? "shadow" : "other");
        } catch {
          resolve("other");
        }
      });
    });
    request.on("timeout", () => request.destroy());
    request.on("error", (error) => resolve(error.code === "ECONNREFUSED" || error.code === "ECONNRESET" ? "none" : "other"));
  });
}

async function checkHealth() {
  return (await probeBackend()) === "shadow";
}

function remember(chunk) {
  const lines = String(chunk).split(/\r?\n/).filter(Boolean);
  backend.log = [...backend.log, ...lines].slice(-LOG_LINES_KEPT);
}

function failBackend(detail) {
  backend.state = "failed";
  backend.detail = detail;
}

async function waitForBackend(startedAt) {
  if (backend.state !== "starting") return;
  if (await checkHealth()) {
    backend.state = "running";
    backend.detail = `The backend was started by the app, at ${BACKEND_URL.origin}.`;
    return;
  }
  if (Date.now() - startedAt > BACKEND_BOOT_TIMEOUT_MS) {
    failBackend(`The backend did not respond within ${BACKEND_BOOT_TIMEOUT_MS / 1000} seconds. Last message: ${backend.log.at(-1) ?? "niciunul"}`);
    return;
  }
  setTimeout(() => void waitForBackend(startedAt), BACKEND_POLL_MS);
}

function startBackend() {
  const port = BACKEND_URL.port || "8000";
  backend.state = "starting";
  backend.detail = "Starting the backend from the backend/ folder (uv run uvicorn). The first start can take a minute while dependencies install.";
  // `shell: true` ca Windows să găsească uv.exe din PATH; `detached` (POSIX) ca să putem opri tot grupul de procese.
  const child = spawn("uv", ["run", "uvicorn", "app.main:app", "--port", port], {
    cwd: BACKEND_DIR,
    shell: true,
    windowsHide: true,
    detached: process.platform !== "win32",
    stdio: ["ignore", "pipe", "pipe"],
  });
  backend.process = child;
  child.stdout.on("data", remember);
  child.stderr.on("data", remember);
  child.on("error", () => failBackend("Could not run the `uv` command. Install uv (https://docs.astral.sh/uv/) or start the backend by hand."));
  child.on("exit", (code) => {
    backend.process = null;
    if (backend.state === "starting" || backend.state === "running") {
      const missing = backend.log.some((line) => /not recognized|not found|nu este recunoscut/i.test(line));
      failBackend(
        missing
          ? "The `uv` command is not on this computer. Install uv (https://docs.astral.sh/uv/) or start the backend by hand."
          : `The backend stopped (code ${code}). Last message: ${backend.log.at(-1) ?? "niciunul"}`,
      );
    }
  });
  void waitForBackend(Date.now());
}

async function ensureBackend() {
  const found = await probeBackend();
  if (found === "other") {
    failBackend(`Port ${BACKEND_URL.port || "8000"} is taken by another program, not by the SHADOW backend. Close that program (for example another dev server) and restart SHADOW.`);
    return;
  }
  if (found === "shadow") {
    backend.state = "external";
    backend.detail = `The backend is already running at ${BACKEND_URL.origin}.`;
    return;
  }
  if (process.env.SHADOW_NO_BACKEND === "1") {
    backend.detail = `The backend is not responding at ${BACKEND_URL.origin}, and starting it automatically is turned off (SHADOW_NO_BACKEND=1).`;
    return;
  }
  if (!fs.existsSync(path.join(BACKEND_DIR, "pyproject.toml"))) {
    backend.detail = `The backend is not responding at ${BACKEND_URL.origin} and the backend/ folder was not found next to frontend/.`;
    return;
  }
  startBackend();
}

function stopBackend() {
  const child = backend.process;
  if (!child?.pid) return;
  backend.state = "disabled";
  if (process.platform === "win32") {
    execFile("taskkill", ["/pid", String(child.pid), "/T", "/F"], () => {});
    return;
  }
  try {
    process.kill(-child.pid, "SIGTERM");
  } catch {
    child.kill("SIGTERM");
  }
}

// ---------------------------------------------------------------- serverul local: fișiere + proxy

function proxyToBackend(request, response) {
  const upstream = http.request(
    {
      protocol: BACKEND_URL.protocol,
      hostname: BACKEND_URL.hostname,
      port: BACKEND_URL.port,
      path: request.url,
      method: request.method,
      headers: { ...request.headers, host: BACKEND_URL.host },
    },
    (reply) => {
      response.writeHead(reply.statusCode ?? 502, reply.headers);
      response.flushHeaders(); // fluxul de evenimente trebuie să plece imediat, fără tampon
      reply.pipe(response);
    },
  );
  upstream.on("error", () => {
    if (response.headersSent) return response.end();
    response.writeHead(502, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ error: { code: "backend_unreachable", message: "The SHADOW server is not responding. Check that the backend is running.", details: null } }));
  });
  response.on("close", () => upstream.destroy());
  request.pipe(upstream);
}

/** Găsește fișierul din `out/` pentru o cale; `null` dacă nu există sau iese din folder. */
function resolveStatic(urlPath) {
  const clean = decodeURIComponent(urlPath.split("?")[0]).replace(/\/+$/, "") || "/index";
  const base = path.join(OUT_DIR, clean);
  if (!base.startsWith(OUT_DIR)) return null;
  return [base, `${base}.html`, path.join(base, "index.html")].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) ?? null;
}

function serveStatic(request, response) {
  const file = resolveStatic(request.url ?? "/");
  const target = file ?? path.join(OUT_DIR, "404.html");
  if (!fs.existsSync(target)) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    return response.end("The frontend is not built. Run: npm run build:app");
  }
  const immutable = (request.url ?? "").startsWith("/_next/static/");
  response.writeHead(file ? 200 : 404, {
    "content-type": MIME[path.extname(target)] ?? "application/octet-stream",
    "cache-control": immutable ? "public, max-age=31536000, immutable" : "no-cache",
  });
  fs.createReadStream(target).pipe(response);
}

function startLocalServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((request, response) => {
      const url = request.url ?? "/";
      if (url.startsWith("/api/") || url === "/health") return proxyToBackend(request, response);
      return serveStatic(request, response);
    });
    server.on("error", reject);
    // port 0 = unul liber, ales de sistem; doar pe 127.0.0.1, deci invizibil din rețea
    server.listen(0, "127.0.0.1", () => resolve(`http://127.0.0.1:${server.address().port}`));
  });
}

// ---------------------------------------------------------------- ferestre

let appUrl = DEV_URL;

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1080,
    minHeight: 680,
    show: false,
    title: "SHADOW",
    backgroundColor: BACKGROUND,
    icon: path.join(__dirname, process.platform === "win32" ? "icon.ico" : "icon.png"),
    // bara de titlu a sistemului (închisă la culoare, prin nativeTheme "dark"); pe macOS, butoanele stau peste antet
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.once("ready-to-show", () => window.show());

  // linkurile spre surse (NASA, articole) se deschid în browserul sistemului, nu în aplicație
  const isExternal = (url) => /^https?:/.test(url) && !url.startsWith(appUrl);
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (isExternal(url)) void shell.openExternal(url);
    return { action: "deny" };
  });
  window.webContents.on("will-navigate", (event, url) => {
    if (!isExternal(url)) return;
    event.preventDefault();
    void shell.openExternal(url);
  });

  void window.loadURL(`${appUrl}/login`);
  return window;
}

function buildMenu() {
  return Menu.buildFromTemplate([
    {
      label: "SHADOW",
      submenu: [
        // fiecare fereastră are sesiunea ei: nava și Pământul pot sta una lângă alta
        { label: "New window", accelerator: "CmdOrCtrl+N", click: () => createWindow() },
        { type: "separator" },
        { label: "Reload", role: "reload" },
        { label: "Developer tools", role: "toggleDevTools" },
        { type: "separator" },
        { label: "Zoom in", role: "zoomIn" },
        { label: "Zoom out", role: "zoomOut" },
        { label: "Actual size", role: "resetZoom" },
        { label: "Full screen", role: "togglefullscreen" },
        { type: "separator" },
        { label: "Quit", role: "quit" },
      ],
    },
    { label: "Edit", role: "editMenu" },
  ]);
}

app.whenReady().then(async () => {
  nativeTheme.themeSource = "dark";
  Menu.setApplicationMenu(buildMenu());
  ipcMain.handle("shadow:backend-status", () => ({ state: backend.state, detail: backend.detail, url: BACKEND_URL.origin }));
  await ensureBackend();
  appUrl ??= await startLocalServer();
  createWindow();
  app.on("activate", () => {
    if (!BrowserWindow.getAllWindows().length) createWindow();
  });
});

app.on("window-all-closed", () => app.quit());
app.on("before-quit", stopBackend);
process.on("exit", stopBackend);
