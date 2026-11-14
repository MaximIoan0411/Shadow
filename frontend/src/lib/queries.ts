"use client";
/**
 * Citirile din API, ca hook-uri TanStack Query. Nu există polling: datele se reîncarcă atunci când un eveniment
 * live le invalidează (vezi `events.tsx`) sau după o scriere făcută de utilizator.
 *
 * Cheile sunt ierarhice, ca un eveniment să poată invalida un grup întreg: `["crew", id]` acoperă tabloul de
 * bord, panourile, derulatorul, check-in-ul, exercițiile și tastarea acelui membru.
 */
import { QueryClient, useQuery, type UseQueryResult } from "@tanstack/react-query";
import { ApiError, ERROR_CODE, type Schemas } from "./api";
import * as api from "./endpoints";

type Query<TData> = UseQueryResult<TData, ApiError>;
type Pillar = Schemas["Pillar"];

const NOW = "now";
const MAX_RETRIES = 2;

export const keys = {
  accounts: ["accounts"],
  mission: ["mission"],
  environments: ["environments"],
  crewList: ["crew-list"],
  crew: (crewId: string) => ["crew", crewId],
  dashboard: (crewId: string, asOfDay?: number) => ["crew", crewId, "dashboard", asOfDay ?? NOW],
  pillar: (crewId: string, pillar: Pillar, asOfDay?: number) => ["crew", crewId, "pillar", pillar, asOfDay ?? NOW],
  timeline: (crewId: string) => ["crew", crewId, "timeline"],
  checkinToday: (crewId: string) => ["crew", crewId, "checkin-today"],
  keystrokes: (crewId: string) => ["crew", crewId, "keystrokes"],
  pvt: (crewId: string) => ["crew", crewId, "pvt"],
  exerciseToday: (crewId: string) => ["crew", crewId, "exercise-today"],
  exerciseSessions: (crewId: string) => ["crew", crewId, "exercise-sessions"],
  checkinSchema: ["checkin-schema"],
  alerts: ["alerts"],
  alertList: (crewId: string) => ["alerts", "list", crewId],
  cmoQueue: ["alerts", "cmo-queue"],
  alert: (alertId: string) => ["alerts", "detail", alertId],
  catalog: ["catalog"],
  link: ["link"],
  linkStatus: ["link", "status"],
  packets: ["link", "packets"],
  packet: (packetId: string) => ["link", "packet", packetId],
  messages: (crewId: string) => ["link", "messages", crewId],
  radiation: ["radiation"],
  radiationStatus: ["radiation", "status"],
  radiationSeries: ["radiation", "series"],
  aiStatus: ["ai-status"],
  security: ["security"],
  accessLog: ["security", "access-log"],
  accessLogIntegrity: ["security", "access-log-integrity"],
  rejections: ["security", "rejections"],
  tests: ["evidence", "tests"],
  parameters: ["evidence", "parameters"],
} as const;

/** Reîncearcă doar când backend-ul nu răspunde; un 403 sau 404 nu se rezolvă repetând cererea. */
const shouldRetry = (failures: number, error: unknown): boolean =>
  error instanceof ApiError && error.code === ERROR_CODE.unreachable && failures < MAX_RETRIES;

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: Infinity, refetchOnWindowFocus: false, refetchOnReconnect: false, retry: shouldRetry },
      mutations: { retry: false },
    },
  });
}

// ---------------------------------------------------------------- fără sesiune

export const useAccounts = (): Query<Schemas["LoginAccount"][]> => useQuery({ queryKey: keys.accounts, queryFn: api.listAccounts });

// ---------------------------------------------------------------- misiune

export const useMission = (enabled = true): Query<Schemas["MissionState"]> =>
  useQuery({ queryKey: keys.mission, queryFn: api.getMission, enabled });

export const useEnvironments = (enabled = true): Query<Schemas["EnvironmentInfo"][]> =>
  useQuery({ queryKey: keys.environments, queryFn: api.listEnvironments, enabled });

// ---------------------------------------------------------------- un membru al echipajului

export const useDashboard = (crewId: string | null, asOfDay?: number): Query<Schemas["Dashboard"]> =>
  useQuery({
    queryKey: keys.dashboard(crewId ?? "", asOfDay),
    queryFn: () => api.getDashboard(crewId ?? "", asOfDay),
    enabled: Boolean(crewId),
    placeholderData: (previous) => previous, // la derulare, ziua veche rămâne pe ecran până sosește cea nouă
  });

export const usePillar = (crewId: string | null, pillar: Pillar | null, asOfDay?: number): Query<Schemas["PillarDetail"]> =>
  useQuery({
    queryKey: keys.pillar(crewId ?? "", pillar ?? "behavioral", asOfDay),
    queryFn: () => api.getPillar(crewId ?? "", pillar ?? "behavioral", asOfDay),
    enabled: Boolean(crewId && pillar),
  });

export const useTimeline = (crewId: string | null): Query<Schemas["Timeline"]> =>
  useQuery({ queryKey: keys.timeline(crewId ?? ""), queryFn: () => api.getTimeline(crewId ?? ""), enabled: Boolean(crewId) });

export const useCheckinSchema = (): Query<Schemas["CheckinSchema"]> =>
  useQuery({ queryKey: keys.checkinSchema, queryFn: api.getCheckinSchema });

export const useCheckinToday = (crewId: string | null): Query<Schemas["Checkin"] | null> =>
  useQuery({ queryKey: keys.checkinToday(crewId ?? ""), queryFn: () => api.getCheckinToday(crewId ?? ""), enabled: Boolean(crewId) });

export const useKeystrokeSummary = (crewId: string | null): Query<Schemas["KeystrokeSummary"]> =>
  useQuery({ queryKey: keys.keystrokes(crewId ?? ""), queryFn: () => api.getKeystrokeSummary(crewId ?? ""), enabled: Boolean(crewId) });

export const usePvtHistory = (crewId: string | null): Query<Schemas["PvtResult"][]> =>
  useQuery({ queryKey: keys.pvt(crewId ?? ""), queryFn: () => api.listPvt(crewId ?? ""), enabled: Boolean(crewId) });

export const useExerciseToday = (crewId: string | null): Query<Schemas["ExerciseToday"]> =>
  useQuery({ queryKey: keys.exerciseToday(crewId ?? ""), queryFn: () => api.getExerciseToday(crewId ?? ""), enabled: Boolean(crewId) });

export const useMessages = (crewId: string | null): Query<Schemas["CrewMessage"][]> =>
  useQuery({ queryKey: keys.messages(crewId ?? ""), queryFn: () => api.listMessages(crewId ?? ""), enabled: Boolean(crewId) });

// ---------------------------------------------------------------- alerte

export const useAlerts = (crewId: string | null): Query<Schemas["AlertBrief"][]> =>
  useQuery({ queryKey: keys.alertList(crewId ?? ""), queryFn: () => api.listAlerts(crewId ?? ""), enabled: Boolean(crewId) });

export const useCmoQueue = (enabled: boolean): Query<Schemas["AlertBrief"][]> =>
  useQuery({ queryKey: keys.cmoQueue, queryFn: api.getCmoQueue, enabled });

export const useCrewList = (enabled: boolean): Query<Schemas["CrewSummary"][]> =>
  useQuery({ queryKey: keys.crewList, queryFn: api.listCrew, enabled });

export const useAlert = (alertId: string | null): Query<Schemas["Alert"]> =>
  useQuery({ queryKey: keys.alert(alertId ?? ""), queryFn: () => api.getAlert(alertId ?? ""), enabled: Boolean(alertId) });

export const useCatalog = (enabled: boolean): Query<Schemas["Recommendation"][]> =>
  useQuery({ queryKey: keys.catalog, queryFn: api.listRecommendations, enabled });

// ---------------------------------------------------------------- legătura cu Pământul

export const useLinkStatus = (enabled = true): Query<Schemas["LinkStatus"]> =>
  useQuery({ queryKey: keys.linkStatus, queryFn: api.getLinkStatus, enabled });

export const usePackets = (enabled: boolean): Query<Schemas["Packet"][]> =>
  useQuery({ queryKey: keys.packets, queryFn: api.listPackets, enabled });

export const usePacket = (packetId: string | null): Query<Schemas["PacketDetail"]> =>
  useQuery({ queryKey: keys.packet(packetId ?? ""), queryFn: () => api.getPacket(packetId ?? ""), enabled: Boolean(packetId) });

// ---------------------------------------------------------------- radiații, AI, dovezi

export const useRadiationStatus = (enabled: boolean): Query<Schemas["RadiationStatus"]> =>
  useQuery({ queryKey: keys.radiationStatus, queryFn: api.getRadiationStatus, enabled });

export const useRadiationSeries = (enabled: boolean): Query<Schemas["RadiationSeries"]> =>
  useQuery({ queryKey: keys.radiationSeries, queryFn: api.getRadiationSeries, enabled });

export const useAiStatus = (enabled: boolean): Query<Schemas["AiStatus"]> =>
  useQuery({ queryKey: keys.aiStatus, queryFn: api.getAiStatus, enabled });

export const useAccessLog = (enabled: boolean): Query<Schemas["AccessLogEntry"][]> =>
  useQuery({ queryKey: keys.accessLog, queryFn: api.listAccessLog, enabled });

/** Lanțul de hash-uri al întregului jurnal, recalculat de backend la fiecare cerere. */
export const useAccessLogIntegrity = (enabled: boolean): Query<Schemas["AccessLogIntegrity"]> =>
  useQuery({ queryKey: keys.accessLogIntegrity, queryFn: api.getAccessLogIntegrity, enabled });

export const useRejections = (enabled: boolean): Query<Schemas["Rejection"][]> =>
  useQuery({ queryKey: keys.rejections, queryFn: api.listRejections, enabled });

export const useTestReport = (): Query<Schemas["TestReport"]> => useQuery({ queryKey: keys.tests, queryFn: api.getTestReport });

export const useParameters = (): Query<Schemas["Parameter"][]> => useQuery({ queryKey: keys.parameters, queryFn: api.listParameters });
