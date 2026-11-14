/**
 * SHADOW — client API pentru frontend. Copiați acest fișier în src/lib/api.ts,
 * iar shadow-api.d.ts lângă el.
 *
 *   npm i openapi-fetch @microsoft/fetch-event-source
 *   npm i -D openapi-typescript
 *
 * Tot ce apelați e verificat de TypeScript față de contract: căi, parametri, corpul cererii, răspunsul.
 */
import createClient, { type Middleware } from "openapi-fetch";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import type { components, paths } from "./shadow-api";

export type Schemas = components["schemas"];
export type Dashboard = Schemas["Dashboard"];
export type PillarDetail = Schemas["PillarDetail"];
export type Alert = Schemas["Alert"];
export type AlertBrief = Schemas["AlertBrief"];
export type Packet = Schemas["Packet"];
export type RadiationStatus = Schemas["RadiationStatus"];
export type SseEvent = Schemas["SseEvent"];
export type User = Schemas["User"];

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Tokenul stă în memorie, nu în localStorage. */
let token: string | null = null;
export const setToken = (t: string | null) => { token = t; };
export const getToken = () => token;

/** Eroarea standard a API-ului: { error: { code, message, details } }. */
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) {
    super(message);
  }
}

const auth: Middleware = {
  async onRequest({ request }) {
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  async onResponse({ response }) {
    if (!response.ok) {
      const body = await response.clone().json().catch(() => null);
      const e = body?.error;
      throw new ApiError(response.status, e?.code ?? "http_error", e?.message ?? response.statusText, e?.details);
    }
    return response;
  },
};

/**
 * Clientul tipizat. Exemple:
 *   const { data } = await client.GET("/api/v1/crew/{crew_id}/dashboard", { params: { path: { crew_id } } });
 *   await client.POST("/api/v1/crew/{crew_id}/checkins", { params: { path: { crew_id } }, body: { mood: 4 } });
 * La orice răspuns 4xx/5xx se aruncă ApiError (code + message în română).
 */
export const client = createClient<paths>({ baseUrl: BASE_URL });
client.use(auth);

/** Conturile pentru ecranul „Cine ești?” (fără token). Fiecare astronaut are contul lui. */
export async function listAccounts(): Promise<Schemas["LoginAccount"][]> {
  const { data } = await client.GET("/api/v1/auth/accounts");
  return data ?? [];
}

/** Autentificare cu contul PERSONAL: salvează tokenul și întoarce utilizatorul (cu role și crew_id). */
export async function login(username: string, password: string): Promise<User> {
  const { data } = await client.POST("/api/v1/auth/login", { body: { username, password } });
  setToken(data!.access_token);
  return data!.user;
}

/**
 * Deconectare. Înainte de ea: opriți colectorul de tastare și închideți abonarea la evenimente.
 * După ea: ștergeți toate datele încărcate, ca să nu rămână pe ecran pentru următorul astronaut.
 */
export async function logout(): Promise<void> {
  try {
    if (token) await client.POST("/api/v1/auth/logout");
  } finally {
    setToken(null);
  }
}

/**
 * Abonare la evenimentele live. Întoarce o funcție care închide conexiunea.
 *   const stop = subscribe((ev) => { if (ev.type === "alert.created") refresh(); }, () => refresh());
 * `onReconnect` se apelează după o reconectare: reîncărcați datele ecranului (evenimentele pierdute nu se retrimit).
 */
export function subscribe(onEvent: (ev: SseEvent) => void, onReconnect?: () => void): () => void {
  const ctrl = new AbortController();
  let opened = false;
  void fetchEventSource(`${BASE_URL}/api/v1/events`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: ctrl.signal,
    openWhenHidden: true, // nu închide fluxul când tabul nu e vizibil (important în demo)
    async onopen() {
      if (opened) onReconnect?.();
      opened = true;
    },
    onmessage(msg) {
      if (!msg.data) return; // comentariile „: ping” nu au date
      onEvent(JSON.parse(msg.data) as SseEvent);
    },
    onerror() {
      /* fără throw → biblioteca reîncearcă singură */
    },
  });
  return () => ctrl.abort();
}

/**
 * Colectorul de tastare: DOAR timpi și clasa tastei, niciodată caracterul.
 *   const ks = createKeystrokeCollector(crewId, "free_typing", (r) => setLive(r));
 *   <textarea onKeyDown={ks.onKeyDown} onKeyUp={ks.onKeyUp} />
 */
type KeyClass = Schemas["KeyEvent"]["key_class"];
const classify = (key: string): KeyClass =>
  key === "Backspace" ? "backspace" : key === " " ? "space" : key === "Enter" ? "enter" : key.length === 1 ? "char" : "other";

export function createKeystrokeCollector(
  crewId: string,
  context: Schemas["KeystrokeBatch"]["context"],
  onResult?: (r: Schemas["KeystrokeResult"]) => void,
) {
  const sessionId = crypto.randomUUID();
  const down = new Map<string, number>();
  let buffer: Schemas["KeyEvent"][] = [];

  async function flush() {
    if (!buffer.length) return;
    const events = buffer;
    buffer = [];
    const { data } = await client.POST("/api/v1/crew/{crew_id}/keystrokes/batches", {
      params: { path: { crew_id: crewId } },
      body: { session_id: sessionId, context, events },
    });
    if (data) onResult?.(data);
  }
  const timer = setInterval(() => void flush(), 5000);

  return {
    onKeyDown(e: { code: string; repeat?: boolean }) {
      if (!e.repeat && !down.has(e.code)) down.set(e.code, performance.now());
    },
    onKeyUp(e: { code: string; key: string }) {
      const t = down.get(e.code);
      if (t === undefined) return;
      down.delete(e.code);
      buffer.push({ t_down_ms: t, t_up_ms: performance.now(), key_class: classify(e.key) });
      if (buffer.length >= 200) void flush();
    },
    stop() {
      clearInterval(timer);
      return flush();
    },
  };
}
