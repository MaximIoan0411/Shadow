/**
 * SHADOW — clientul API al frontend-ului.
 *
 * Toate cererile merg pe ACEEAȘI ORIGINE, la `/api/v1/…`. Cine le duce la backend:
 *   - în `npm run dev`: regula `rewrites` din next.config.ts (spre SHADOW_API_URL, implicit http://127.0.0.1:8000);
 *   - în aplicația Electron: proxy-ul din electron/main.cjs.
 * Așa frontend-ul nu știe adresa backend-ului și nu depinde de CORS.
 *
 * Tot ce apelați e verificat de TypeScript față de contract (`shadow-api.d.ts`): căi, parametri, corp, răspuns.
 */
import createClient, { type Middleware } from "openapi-fetch";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import type { components, paths } from "./shadow-api";

export type Schemas = components["schemas"];
export type SseEvent = Schemas["SseEvent"];
export type User = Schemas["User"];

/** Eroarea standard a API-ului: `{ error: { code, message, details } }`. `message` e în română, gata de afișat. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export const ERROR_CODE = {
  unauthorized: "unauthorized",
  invalidCredentials: "invalid_credentials",
  tooManyAttempts: "too_many_attempts",
  forbidden: "forbidden",
  notFound: "not_found",
  invalidState: "invalid_state",
  validation: "validation_error",
  unreachable: "backend_unreachable",
} as const;

const EVENTS_PATH = "/api/v1/events";
const HEALTH_PATH = "/health";
const UNREACHABLE_STATUS = 503;
const SERVER_ERROR_FROM = 500;
const UNREACHABLE_MESSAGE = "The SHADOW server is not responding. Check that the backend is running.";
const GENERIC_MESSAGE = "Something unexpected went wrong. Try again.";
const KEYSTROKE_FLUSH_MS = 5000;
const KEYSTROKE_BATCH_SIZE = 200;

/** Tokenul stă doar în memorie: la închiderea ferestrei sau la reîncărcare, sesiunea dispare. */
let token: string | null = null;
let onUnauthorized: (() => void) | null = null;

export const setToken = (value: string | null): void => {
  token = value;
};
export const getToken = (): string | null => token;

/** Sesiunea se înscrie aici ca să afle când serverul refuză tokenul (401) și să trimită la autentificare. */
export const setUnauthorizedHandler = (handler: (() => void) | null): void => {
  onUnauthorized = handler;
};

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null;

/** Citește corpul unei erori în forma contractului; orice altceva (HTML de la proxy, text gol) devine `null`. */
async function readErrorBody(response: Response): Promise<{ code?: string; message?: string; details?: unknown } | null> {
  try {
    const body: unknown = await response.clone().json();
    const error = isRecord(body) ? body.error : null;
    if (!isRecord(error)) return null;
    return {
      code: typeof error.code === "string" ? error.code : undefined,
      message: typeof error.message === "string" ? error.message : undefined,
      details: error.details,
    };
  } catch {
    return null;
  }
}

const auth: Middleware = {
  async onRequest({ request }) {
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  async onResponse({ response }) {
    if (response.ok) return response;
    const body = await readErrorBody(response);
    // Un 5xx fără corp în forma contractului vine de la proxy, nu de la backend: backend-ul nu e pornit.
    const fromProxy = !body && response.status >= SERVER_ERROR_FROM;
    const code = body?.code ?? (fromProxy ? ERROR_CODE.unreachable : "http_error");
    const fallback = fromProxy ? UNREACHABLE_MESSAGE : GENERIC_MESSAGE;
    const error = new ApiError(response.status, code, body?.message ?? fallback, body?.details);
    if (code === ERROR_CODE.unauthorized) onUnauthorized?.();
    throw error;
  },
  onError() {
    return new ApiError(UNREACHABLE_STATUS, ERROR_CODE.unreachable, UNREACHABLE_MESSAGE);
  },
};

/**
 * Clientul tipizat. Exemple:
 *   const { data } = await client.GET("/api/v1/crew/{crew_id}/dashboard", { params: { path: { crew_id } } });
 *   await client.POST("/api/v1/crew/{crew_id}/checkins", { params: { path: { crew_id } }, body: { mood: 4 } });
 * La orice răspuns 4xx/5xx se aruncă ApiError (code + message în română).
 */
export const client = createClient<paths>({ baseUrl: "" });
client.use(auth);

/** Scoate `data` dintr-un răspuns reușit. Un răspuns 2xx fără corp e o încălcare a contractului. */
export function unwrap<TData>(result: { readonly data?: TData }): TData {
  if (result.data === undefined) throw new ApiError(0, "empty_response", "The server responded without data.");
  return result.data;
}

/** Mesajul de afișat pentru orice eroare prinsă: al API-ului dacă există, altfel unul generic. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : GENERIC_MESSAGE;
}

interface Health {
  readonly ok: boolean;
  readonly version?: string;
  readonly mode?: string;
}

/** Verifică dacă backend-ul răspunde (`GET /health`), fără token. */
export async function checkHealth(): Promise<Health> {
  try {
    const response = await fetch(HEALTH_PATH, { cache: "no-store" });
    if (!response.ok) return { ok: false };
    const body: unknown = await response.json();
    if (!isRecord(body)) return { ok: false };
    return {
      ok: body.ok === true,
      version: typeof body.version === "string" ? body.version : undefined,
      mode: typeof body.mode === "string" ? body.mode : undefined,
    };
  } catch {
    return { ok: false };
  }
}

const SSE_TYPES: ReadonlySet<string> = new Set<SseEvent["type"]>([
  "mission.tick",
  "environment.changed",
  "alert.created",
  "alert.updated",
  "packet.sent",
  "packet.arrived",
  "packet.rejected",
  "radiation.alert",
  "radiation.reading",
  "radiation.cleared",
  "measurement.rejected",
  "reminder.due",
  "dashboard.changed",
]);

/** Validează plicul unui eveniment la intrarea în aplicație; mesajele necunoscute se ignoră. */
function parseEvent(raw: string): SseEvent | null {
  try {
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value) || typeof value.type !== "string" || !SSE_TYPES.has(value.type) || !isRecord(value.data)) return null;
    // Plicul a fost verificat mai sus (tip cunoscut + `data` obiect); restul câmpurilor sunt garantate de contract.
    return value as SseEvent;
  } catch {
    return null;
  }
}

interface Subscription {
  readonly onEvent: (event: SseEvent) => void;
  /** După o reconectare evenimentele pierdute NU se retrimit: reîncărcați datele ecranului. */
  readonly onReconnect?: () => void;
  readonly onStatus?: (connected: boolean) => void;
}

/** Abonare la evenimentele live. Întoarce funcția care închide conexiunea. */
export function subscribe({ onEvent, onReconnect, onStatus }: Subscription): () => void {
  const controller = new AbortController();
  const state = { opened: false };
  void fetchEventSource(EVENTS_PATH, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: controller.signal,
    openWhenHidden: true, // nu închide fluxul când fereastra nu e în față (important în demo)
    async onopen(response) {
      if (!response.ok) throw new ApiError(response.status, "sse_refused", "The event stream was refused.");
      if (state.opened) onReconnect?.();
      state.opened = true;
      onStatus?.(true);
    },
    onmessage(message) {
      if (!message.data) return; // comentariile „: ping” nu au date
      const event = parseEvent(message.data);
      if (event) onEvent(event);
    },
    onclose() {
      onStatus?.(false);
    },
    onerror() {
      onStatus?.(false); // fără throw → biblioteca reîncearcă singură
    },
  });
  return () => controller.abort();
}

type KeyClass = Schemas["KeyEvent"]["key_class"];
type KeystrokeContext = Schemas["KeystrokeBatch"]["context"];

const SPECIAL_KEYS: Readonly<Record<string, KeyClass>> = { Backspace: "backspace", " ": "space", Enter: "enter" };

/** Clasa tastei. Caracterul propriu-zis nu părăsește niciodată această funcție. */
const classify = (key: string): KeyClass => SPECIAL_KEYS[key] ?? (key.length === 1 ? "char" : "other");

export interface KeystrokeCollector {
  readonly onKeyDown: (event: { readonly code: string; readonly repeat?: boolean }) => void;
  readonly onKeyUp: (event: { readonly code: string; readonly key: string }) => void;
  /** Trimite ce a rămas și oprește colectorul. Se apelează la schimbarea astronautului. */
  readonly stop: () => Promise<void>;
}

/**
 * Colectorul de tastare: DOAR timpi și clasa tastei, niciodată caracterul.
 *   const ks = createKeystrokeCollector(crewId, "free_typing", { onResult, onStroke });
 *   <textarea onKeyDown={ks.onKeyDown} onKeyUp={ks.onKeyUp} />
 */
export function createKeystrokeCollector(
  crewId: string,
  context: KeystrokeContext,
  handlers: {
    readonly onResult?: (result: Schemas["KeystrokeResult"]) => void;
    /** Durata fiecărei apăsări, în ms, pentru barele live. */
    readonly onStroke?: (holdMs: number, keyClass: KeyClass) => void;
    readonly onError?: (error: unknown) => void;
  } = {},
): KeystrokeCollector {
  const sessionId = crypto.randomUUID();
  const down = new Map<string, number>();
  const state: { buffer: Schemas["KeyEvent"][] } = { buffer: [] };

  async function flush(): Promise<void> {
    if (!state.buffer.length) return;
    const events = state.buffer;
    state.buffer = [];
    try {
      const result = await client.POST("/api/v1/crew/{crew_id}/keystrokes/batches", {
        params: { path: { crew_id: crewId } },
        body: { session_id: sessionId, context, events },
      });
      if (result.data) handlers.onResult?.(result.data);
    } catch (error) {
      handlers.onError?.(error);
    }
  }
  const timer = setInterval(() => void flush(), KEYSTROKE_FLUSH_MS);

  return {
    onKeyDown(event) {
      if (!event.repeat && !down.has(event.code)) down.set(event.code, performance.now());
    },
    onKeyUp(event) {
      const startedAt = down.get(event.code);
      if (startedAt === undefined) return;
      down.delete(event.code);
      const endedAt = performance.now();
      const keyClass = classify(event.key);
      state.buffer.push({ t_down_ms: startedAt, t_up_ms: endedAt, key_class: keyClass });
      handlers.onStroke?.(endedAt - startedAt, keyClass);
      if (state.buffer.length >= KEYSTROKE_BATCH_SIZE) void flush();
    },
    async stop() {
      clearInterval(timer);
      await flush();
    },
  };
}
