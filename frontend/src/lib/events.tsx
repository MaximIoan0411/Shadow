"use client";
/**
 * Evenimentele live: UN SINGUR abonament la `/api/v1/events`, deschis cât e cineva autentificat.
 * Fiecare eveniment invalidează datele pe care le privește (tabelul din contract, secțiunea 6); ecranele nu
 * deschid conexiuni proprii și nu fac polling. După o reconectare se reîncarcă tot: evenimentele pierdute nu
 * se retrimit.
 */
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState, type ReactElement, type ReactNode } from "react";
import { subscribe, type Schemas, type SseEvent } from "./api";
import { keys } from "./queries";
import { useSession } from "./session";
import type { Status } from "./status";
import { useToast, type ToastInput } from "./toast";

type EventType = SseEvent["type"];
type EventData = SseEvent["data"];

interface HandlerContext {
  readonly queryClient: QueryClient;
  readonly notify: (toast: ToastInput) => void;
  readonly role: Schemas["Role"];
}

type Handler = (event: SseEvent, context: HandlerContext) => void;

const RESET_REASON = "reset";
const DIRECTION_UP = "up";
const STATUSES: readonly string[] = ["ok", "watch", "alert", "unknown"];
const CREW_SCOPE = ["crew"] as const;

const text = (data: EventData, key: string): string | undefined => {
  const value = data[key];
  return typeof value === "string" ? value : undefined;
};
const number = (data: EventData, key: string): number | undefined => {
  const value = data[key];
  return typeof value === "number" ? value : undefined;
};
const status = (data: EventData, key: string): Status | undefined => {
  const value = text(data, key);
  // `value` e verificat față de lista stărilor din contract chiar înainte.
  return value && STATUSES.includes(value) ? (value as Status) : undefined;
};

const invalidate = (queryClient: QueryClient, ...scopes: readonly (readonly string[])[]): void => {
  scopes.forEach((queryKey) => void queryClient.invalidateQueries({ queryKey }));
};

/** Ceasul vine prin tick, nu printr-o cerere pe secundă; la schimbarea zilei se reîncarcă datele pe zile. */
const onTick: Handler = (event, { queryClient }) => {
  const simNow = text(event.data, "sim_now");
  const missionDay = number(event.data, "mission_day");
  if (!simNow || missionDay === undefined) return;
  const previous = queryClient.getQueryData<Schemas["MissionState"]>(keys.mission);
  if (!previous) return;
  queryClient.setQueryData<Schemas["MissionState"]>(keys.mission, { ...previous, sim_now: simNow, mission_day: missionDay });
  if (previous.mission_day !== missionDay) invalidate(queryClient, CREW_SCOPE);
};

/** În timpul furtunii citirile vin des: starea se scrie direct, iar punctul nou se adaugă la grafic. */
const onRadiationReading: Handler = (event, { queryClient }) => {
  const at = text(event.data, "at");
  const doseRate = number(event.data, "dose_rate_usv_h");
  const mean = number(event.data, "mean_24h_usv_h");
  if (!at || doseRate === undefined || mean === undefined) return invalidate(queryClient, keys.radiation);
  // Câmpurile folosite mai jos au fost verificate; restul stării respectă contractul RadiationStatus.
  queryClient.setQueryData(keys.radiationStatus, event.data as Schemas["RadiationStatus"]);
  const series = queryClient.getQueryData<Schemas["RadiationSeries"]>(keys.radiationSeries);
  if (!series) return;
  const point = { t: at, dose_rate_usv_h: doseRate, mean_24h_usv_h: mean, sheltered: event.data.sheltered === true };
  queryClient.setQueryData<Schemas["RadiationSeries"]>(keys.radiationSeries, { ...series, points: [...series.points, point] });
};

const HANDLERS = {
  "mission.tick": onTick,
  "environment.changed": (_event, { queryClient }) => invalidate(queryClient, keys.mission, keys.link),
  "dashboard.changed": (event, { queryClient }) => {
    if (text(event.data, "reason") === RESET_REASON) return void queryClient.invalidateQueries();
    invalidate(queryClient, CREW_SCOPE, keys.alerts);
  },
  "alert.created": (event, { queryClient, notify }) => {
    invalidate(queryClient, keys.alerts, CREW_SCOPE);
    notify({ title: "New alert", detail: text(event.data, "title"), status: status(event.data, "status") });
  },
  "alert.updated": (_event, { queryClient }) => invalidate(queryClient, keys.alerts, CREW_SCOPE),
  "packet.sent": (_event, { queryClient }) => invalidate(queryClient, keys.link),
  "packet.arrived": (event, { queryClient, notify, role }) => {
    invalidate(queryClient, keys.link, keys.alerts, keys.radiation);
    const fromEarth = text(event.data, "direction") === DIRECTION_UP;
    if (fromEarth && role !== "earth") notify({ title: "Message arrived from Earth", detail: text(event.data, "title") });
    if (!fromEarth && role === "earth") notify({ title: "Packet arrived from the ship", detail: text(event.data, "title") });
  },
  "packet.rejected": (event, { queryClient, notify }) => {
    invalidate(queryClient, keys.link, keys.security);
    notify({ title: "Packet rejected: invalid signature", detail: text(event.data, "title"), status: "alert" });
  },
  "radiation.alert": (_event, { queryClient, notify }) => {
    invalidate(queryClient, keys.radiation, CREW_SCOPE, keys.alerts);
    notify({ title: "Solar storm: go to the shelter", status: "alert" });
  },
  "radiation.reading": onRadiationReading,
  "radiation.cleared": (_event, { queryClient, notify }) => {
    invalidate(queryClient, keys.radiation, CREW_SCOPE);
    notify({ title: "Radiation is back to normal", status: "ok" });
  },
  "measurement.rejected": (event, { queryClient, notify }) => {
    invalidate(queryClient, keys.security);
    notify({ title: "Measurement rejected", detail: text(event.data, "message"), status: "watch" });
  },
  "reminder.due": (event, { queryClient, notify }) => {
    invalidate(queryClient, CREW_SCOPE);
    notify({ title: "Reminder", detail: text(event.data, "label") });
  },
} as const satisfies Record<EventType, Handler>;

type Connection = "connecting" | "open" | "lost";

interface EventsValue {
  /** `connecting` la început, `open` cât curg evenimentele, `lost` cât conexiunea e căzută și se reîncearcă. */
  readonly connection: Connection;
}

const EventsContext = createContext<EventsValue>({ connection: "connecting" });

export const useEvents = (): EventsValue => useContext(EventsContext);

export function EventsProvider({ children }: { readonly children: ReactNode }): ReactElement {
  const { user, onBeforeLogout } = useSession();
  const queryClient = useQueryClient();
  const notify = useToast();
  const [connection, setConnection] = useState<Connection>("connecting");
  const userId = user?.id;
  const role = user?.role;

  useEffect(() => {
    if (!userId || !role) return undefined;
    const context: HandlerContext = { queryClient, notify, role };
    const stop = subscribe({
      onEvent: (event) => HANDLERS[event.type](event, context),
      onReconnect: () => void queryClient.invalidateQueries(),
      onStatus: (connected) => setConnection(connected ? "open" : "lost"),
    });
    const unregister = onBeforeLogout(stop);
    return () => {
      unregister();
      stop();
      setConnection("connecting");
    };
  }, [userId, role, queryClient, notify, onBeforeLogout]);

  const value = useMemo<EventsValue>(() => ({ connection }), [connection]);
  return <EventsContext.Provider value={value}>{children}</EventsContext.Provider>;
}
