/**
 * Câte o funcție pentru fiecare endpoint din contract (`backend/handoff/02_CONTRACT_ENDPOINTS.md`).
 * Ecranele nu apelează `client` direct: citirile trec prin hook-urile din `queries.ts`, iar scrierile prin
 * funcțiile de aici. Dacă se schimbă contractul, TypeScript arată aici ce nu mai potrivește.
 */
import { client, unwrap, type Schemas } from "./api";

export type Pillar = Schemas["Pillar"];
export type EnvironmentId = Schemas["EnvironmentId"];

// ---------------------------------------------------------------- autentificare

export async function listAccounts(): Promise<Schemas["LoginAccount"][]> {
  return unwrap(await client.GET("/api/v1/auth/accounts"));
}

export async function login(body: Schemas["LoginRequest"]): Promise<Schemas["LoginResponse"]> {
  return unwrap(await client.POST("/api/v1/auth/login", { body }));
}

export async function logout(): Promise<void> {
  await client.POST("/api/v1/auth/logout");
}

export async function getMe(): Promise<Schemas["User"]> {
  return unwrap(await client.GET("/api/v1/auth/me"));
}

// ---------------------------------------------------------------- misiune, mediu, ceas

export async function getMission(): Promise<Schemas["MissionState"]> {
  return unwrap(await client.GET("/api/v1/mission"));
}

export async function listEnvironments(): Promise<Schemas["EnvironmentInfo"][]> {
  return unwrap(await client.GET("/api/v1/environments"));
}

export async function setEnvironment(environment: EnvironmentId): Promise<Schemas["MissionState"]> {
  return unwrap(await client.PUT("/api/v1/mission/environment", { body: { environment } }));
}

export async function setClock(body: Schemas["ClockUpdate"]): Promise<Schemas["MissionState"]> {
  return unwrap(await client.PUT("/api/v1/sim/clock", { body }));
}

// ---------------------------------------------------------------- echipaj și corpul interactiv

export async function listCrew(): Promise<Schemas["CrewSummary"][]> {
  return unwrap(await client.GET("/api/v1/crew"));
}

export async function getDashboard(crewId: string, asOfDay?: number): Promise<Schemas["Dashboard"]> {
  return unwrap(
    await client.GET("/api/v1/crew/{crew_id}/dashboard", { params: { path: { crew_id: crewId }, query: { as_of_day: asOfDay } } }),
  );
}

export async function getPillar(crewId: string, pillar: Pillar, asOfDay?: number): Promise<Schemas["PillarDetail"]> {
  return unwrap(
    await client.GET("/api/v1/crew/{crew_id}/pillars/{pillar}", {
      params: { path: { crew_id: crewId, pillar }, query: { as_of_day: asOfDay } },
    }),
  );
}

export async function getPillarSeries(
  crewId: string,
  pillar: Pillar,
  query: { readonly metric: string; readonly from_day?: number; readonly to_day?: number },
): Promise<Schemas["MetricSeries"]> {
  return unwrap(
    await client.GET("/api/v1/crew/{crew_id}/pillars/{pillar}/series", { params: { path: { crew_id: crewId, pillar }, query } }),
  );
}

export async function getTimeline(crewId: string): Promise<Schemas["Timeline"]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/timeline", { params: { path: { crew_id: crewId } } }));
}

// ---------------------------------------------------------------- check-in

export async function getCheckinSchema(): Promise<Schemas["CheckinSchema"]> {
  return unwrap(await client.GET("/api/v1/checkin/schema"));
}

/** `null` = încă nu există check-in azi. */
export async function getCheckinToday(crewId: string): Promise<Schemas["Checkin"] | null> {
  const result = await client.GET("/api/v1/crew/{crew_id}/checkins/today", { params: { path: { crew_id: crewId } } });
  return result.data ?? null;
}

export async function listCheckins(crewId: string): Promise<Schemas["Checkin"][]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/checkins", { params: { path: { crew_id: crewId } } }));
}

export async function submitCheckin(crewId: string, body: Schemas["CheckinCreate"]): Promise<Schemas["CheckinResult"]> {
  return unwrap(await client.POST("/api/v1/crew/{crew_id}/checkins", { params: { path: { crew_id: crewId } }, body }));
}

// ---------------------------------------------------------------- tastare și test de reacție

export async function getKeystrokeSummary(crewId: string): Promise<Schemas["KeystrokeSummary"]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/keystrokes/summary", { params: { path: { crew_id: crewId } } }));
}

export async function listPvt(crewId: string): Promise<Schemas["PvtResult"][]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/pvt", { params: { path: { crew_id: crewId } } }));
}

export async function submitPvt(crewId: string, body: Schemas["PvtSubmit"]): Promise<Schemas["PvtResult"]> {
  return unwrap(await client.POST("/api/v1/crew/{crew_id}/pvt", { params: { path: { crew_id: crewId } }, body }));
}

// ---------------------------------------------------------------- exerciții

export async function getExerciseToday(crewId: string): Promise<Schemas["ExerciseToday"]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/exercise/today", { params: { path: { crew_id: crewId } } }));
}

export async function listExerciseSessions(crewId: string): Promise<Schemas["ExerciseSession"][]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/exercise/sessions", { params: { path: { crew_id: crewId } } }));
}

export async function addExerciseSession(crewId: string, body: Schemas["ExerciseSessionCreate"]): Promise<Schemas["ExerciseSession"]> {
  return unwrap(await client.POST("/api/v1/crew/{crew_id}/exercise/sessions", { params: { path: { crew_id: crewId } }, body }));
}

// ---------------------------------------------------------------- alerte, triaj, catalog

export async function listAlerts(crewId: string): Promise<Schemas["AlertBrief"][]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/alerts", { params: { path: { crew_id: crewId } } }));
}

export async function getCmoQueue(): Promise<Schemas["AlertBrief"][]> {
  return unwrap(await client.GET("/api/v1/cmo/queue"));
}

export async function getAlert(alertId: string): Promise<Schemas["Alert"]> {
  return unwrap(await client.GET("/api/v1/alerts/{alert_id}", { params: { path: { alert_id: alertId } } }));
}

export async function ackAlert(alertId: string): Promise<Schemas["Alert"]> {
  return unwrap(await client.POST("/api/v1/alerts/{alert_id}/ack", { params: { path: { alert_id: alertId } } }));
}

export async function setPlanStep(alertId: string, stepId: string, done: boolean): Promise<Schemas["Alert"]> {
  return unwrap(
    await client.PUT("/api/v1/alerts/{alert_id}/plan/steps/{step_id}", {
      params: { path: { alert_id: alertId, step_id: stepId } },
      body: { done },
    }),
  );
}

export async function escalateAlert(alertId: string, body: Schemas["EscalateRequest"]): Promise<Schemas["Alert"]> {
  return unwrap(await client.POST("/api/v1/alerts/{alert_id}/escalate", { params: { path: { alert_id: alertId } }, body }));
}

export async function resolveAlert(alertId: string, body: Schemas["ResolveRequest"]): Promise<Schemas["Alert"]> {
  return unwrap(await client.POST("/api/v1/alerts/{alert_id}/resolve", { params: { path: { alert_id: alertId } }, body }));
}

export async function listRecommendations(): Promise<Schemas["Recommendation"][]> {
  return unwrap(await client.GET("/api/v1/catalog/recommendations"));
}

export async function getRecommendation(recId: string): Promise<Schemas["Recommendation"]> {
  return unwrap(await client.GET("/api/v1/catalog/recommendations/{rec_id}", { params: { path: { rec_id: recId } } }));
}

// ---------------------------------------------------------------- legătura cu Pământul

export async function getLinkStatus(): Promise<Schemas["LinkStatus"]> {
  return unwrap(await client.GET("/api/v1/link/status"));
}

export async function listPackets(): Promise<Schemas["Packet"][]> {
  return unwrap(await client.GET("/api/v1/link/packets"));
}

export async function getPacket(packetId: string): Promise<Schemas["PacketDetail"]> {
  return unwrap(await client.GET("/api/v1/link/packets/{packet_id}", { params: { path: { packet_id: packetId } } }));
}

export async function sendToEarth(body: Schemas["OutboxCreate"]): Promise<Schemas["Packet"]> {
  return unwrap(await client.POST("/api/v1/link/outbox", { body }));
}

export async function replyFromEarth(body: Schemas["EarthReplyCreate"]): Promise<Schemas["Packet"]> {
  return unwrap(await client.POST("/api/v1/earth/replies", { body }));
}

export async function listMessages(crewId: string): Promise<Schemas["CrewMessage"][]> {
  return unwrap(await client.GET("/api/v1/crew/{crew_id}/messages", { params: { path: { crew_id: crewId } } }));
}

// ---------------------------------------------------------------- radiații

export async function getRadiationStatus(): Promise<Schemas["RadiationStatus"]> {
  return unwrap(await client.GET("/api/v1/radiation/status"));
}

export async function getRadiationSeries(): Promise<Schemas["RadiationSeries"]> {
  return unwrap(await client.GET("/api/v1/radiation/series"));
}

export async function ackShelter(sheltered: boolean): Promise<Schemas["RadiationStatus"]> {
  return unwrap(await client.POST("/api/v1/radiation/shelter-ack", { body: { sheltered } }));
}

// ---------------------------------------------------------------- medicul AI

export async function getAiStatus(): Promise<Schemas["AiStatus"]> {
  return unwrap(await client.GET("/api/v1/ai/status"));
}

export async function askAi(body: Schemas["AiChatRequest"]): Promise<Schemas["AiChatResponse"]> {
  return unwrap(await client.POST("/api/v1/ai/chat", { body }));
}

// ---------------------------------------------------------------- securitate și dovezi

export async function listAccessLog(): Promise<Schemas["AccessLogEntry"][]> {
  return unwrap(await client.GET("/api/v1/access-log"));
}

export async function listRejections(): Promise<Schemas["Rejection"][]> {
  return unwrap(await client.GET("/api/v1/security/rejections"));
}

export async function getTestReport(): Promise<Schemas["TestReport"]> {
  return unwrap(await client.GET("/api/v1/evidence/tests"));
}

export async function listParameters(): Promise<Schemas["Parameter"][]> {
  return unwrap(await client.GET("/api/v1/evidence/parameters"));
}

// ---------------------------------------------------------------- demo și simulator

/** Evenimentul real de particule solare din NASA DONKI pe care îl redă simulatorul (furtuna Gannon). */
const DONKI_SEP_EVENT_ID = "2024-05-11T02:10:00-SEP-001";

export async function startStorm(): Promise<Schemas["RadiationStatus"]> {
  return unwrap(await client.POST("/api/v1/sim/sep/start", { body: { event_id: DONKI_SEP_EVENT_ID, starts_in_min: 0 } }));
}

export async function stopStorm(): Promise<Schemas["RadiationStatus"]> {
  return unwrap(await client.POST("/api/v1/sim/sep/stop"));
}

export async function injectSpoofedPacket(): Promise<Schemas["Packet"]> {
  return unwrap(await client.POST("/api/v1/demo/inject-spoof"));
}

export async function triggerFrozenSensor(): Promise<Schemas["Rejection"]> {
  return unwrap(await client.POST("/api/v1/demo/frozen-sensor"));
}

export async function resetSimulation(): Promise<void> {
  await client.POST("/api/v1/sim/reset");
}
