/* eslint-disable ts-patterns/no-magic-numbers -- date de exemplu, scrise de mână, doar pentru catalogul /kit */
/**
 * Exemplele din catalogul sistemului de design. Au forma contractului, dar nu vin din API:
 * ecranele reale nu folosesc niciodată acest fișier.
 */
import type { Schemas } from "@/lib/api";
import type { Status } from "@/lib/status";

export const SAMPLE_PILLARS: readonly Schemas["PillarSummary"][] = [
  { pillar: "behavioral", name: "Typing", body_zone: "brain", status: "watch", score: 71, headline: "You are typing 18% slower than usual", hazard: "isolation", active_alert_id: null },
  { pillar: "cardio", name: "Heart", body_zone: "heart", status: "ok", score: 88, headline: "Within your in-flight baseline", hazard: "gravity", active_alert_id: null },
  { pillar: "immune", name: "Sentinel", body_zone: "immune", status: "alert", score: 58, headline: "Night pulse up 3 nights in a row", hazard: "hostile_environment", active_alert_id: null },
  { pillar: "musculoskeletal", name: "Loading", body_zone: "bones", status: "ok", score: 82, headline: "1 of 2 sessions done today", hazard: "gravity", active_alert_id: null },
];

export const SAMPLE_GAP: Schemas["PerceptionGap"] = {
  self_reported_mood: 4,
  self_score: 80,
  objective_score: 52,
  gap: 28,
  status: "alert",
  explanation: "You say you are fine (4/5), but you are typing 18% slower and your night pulse has risen.",
  contributing_signals: ["Typing: −18% speed", "Night pulse: +7 bpm"],
};

export const NIGHT_PULSE = [54, 53, 55, 54, 54, 56, 60, 61, 61] as const;
export const FIRST_DAY = 88;
export const ALERT_FROM = 60;
export const SAMPLE_DAYS = 140;
export const SAMPLE_TODAY = 96;
const WATCH_DAYS: readonly number[] = [40, 41, 61];
const ALERT_DAYS: readonly number[] = [94, 95, 96];
const SAMPLE_ISO = "2027-04-15T07:42:00Z";

function dayStatus(day: number): Status {
  if (ALERT_DAYS.includes(day)) return "alert";
  return WATCH_DAYS.includes(day) ? "watch" : "ok";
}

export const SAMPLE_TIMELINE: readonly Schemas["TimelineDay"][] = Array.from({ length: SAMPLE_TODAY }, (_, index) => {
  const status = dayStatus(index + 1);
  return { day: index + 1, date: SAMPLE_ISO, overall_status: status, pillars: { behavioral: status, cardio: "ok", immune: status, musculoskeletal: "ok" }, events: [] };
});

export const SAMPLE_PACKET: Schemas["Packet"] = {
  id: "pk-0007",
  seq: 7,
  direction: "down",
  kind: "alert_l3",
  status: "in_transit",
  title: "Immune, night pulse +7 bpm",
  sender: "Crew medical officer",
  created_at: SAMPLE_ISO,
  progress: 0.4,
  eta_real_s: 8,
  size_bytes: 1840,
};
