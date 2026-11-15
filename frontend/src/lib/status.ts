/**
 * Sensul vizual al valorilor din contract: starea are culoare + iconiță + cuvânt (mereu împreună), iar pilonii,
 * subiectele și nivelurile au doar iconiță și nume, fără culoare. Singurul loc din aplicație care leagă un
 * `status` de o culoare.
 */
import { Bone, Brain, CircleCheck, CircleDashed, HeartPulse, OctagonAlert, Radiation, ShieldPlus, TriangleAlert, Waypoints, type LucideIcon } from "lucide-react";
import type { components } from "./shadow-api";

type Schemas = components["schemas"];
export type Status = Schemas["Status"];
export type Pillar = Schemas["Pillar"];
export type AlertTopic = Schemas["AlertTopic"];
export type Level = Schemas["AlertBrief"]["level"];

interface StatusMeta {
  /** Variabila CSS a culorii; `unknown` nu are culoare, e un ton neutru. */
  readonly color: string;
  /** Iconița stării; fiecare are alt contur (cerc, triunghi, octogon), ca starea să se vadă și fără culoare. */
  readonly icon: LucideIcon;
  readonly label: string;
}

export const STATUS_META = {
  ok: { color: "var(--color-ok)", icon: CircleCheck, label: "Within limits" },
  watch: { color: "var(--color-watch)", icon: TriangleAlert, label: "Watch" },
  alert: { color: "var(--color-alert)", icon: OctagonAlert, label: "Alert" },
  unknown: { color: "var(--color-fg-4)", icon: CircleDashed, label: "No data" },
} as const satisfies Record<Status, StatusMeta>;

/** Gravitatea, pentru sortări: poziția în această listă (cea mai gravă e ultima). */
const STATUS_SEVERITY = ["unknown", "ok", "watch", "alert"] as const satisfies readonly Status[];
export const statusRank = (status: Status): number => STATUS_SEVERITY.indexOf(status);

interface PillarMeta {
  readonly icon: LucideIcon;
  /** Partea corpului, cum apare lângă numele pilonului. */
  readonly zone: string;
}

export const PILLAR_META = {
  behavioral: { icon: Brain, zone: "Brain" },
  cardio: { icon: HeartPulse, zone: "Heart" },
  immune: { icon: ShieldPlus, zone: "Immune system" },
  musculoskeletal: { icon: Bone, zone: "Bones and muscles" },
} as const satisfies Record<Pillar, PillarMeta>;

export const PILLAR_ORDER = ["behavioral", "cardio", "immune", "musculoskeletal"] as const satisfies readonly Pillar[];

interface TopicMeta {
  readonly icon: LucideIcon;
  readonly label: string;
}

export const TOPIC_META = {
  behavioral: { icon: Brain, label: "Typing" },
  cardio: { icon: HeartPulse, label: "Heart" },
  immune: { icon: ShieldPlus, label: "Sentinel" },
  musculoskeletal: { icon: Bone, label: "Loading" },
  radiation: { icon: Radiation, label: "Radiation" },
  cross_signal: { icon: Waypoints, label: "Cross signal" },
} as const satisfies Record<AlertTopic, TopicMeta>;

/** Cine se ocupă la fiecare nivel de triaj; poziția în listă e `level` din contract (1–3). */
const LEVEL_LABELS = ["", "Level 1 · handle it yourself", "Level 2 · medical officer", "Level 3 · Earth"] as const;
const LEVEL_SHORTS = ["", "Level 1", "Level 2", "Level 3"] as const;
export const levelLabel = (level: Level): string => LEVEL_LABELS[level];
export const levelShort = (level: Level): string => LEVEL_SHORTS[level];

/** Nivelul ofițerului medical și cel al Pământului, ca ținte ale escaladării. */
export const LEVEL_CMO = 2;
export const LEVEL_EARTH = 3;

export const ALERT_STATE_LABEL = {
  active: "New",
  acknowledged: "Seen",
  escalated: "Escalated",
  resolved: "Closed",
} as const satisfies Record<Schemas["AlertState"], string>;

export const HAZARD_LABEL = {
  radiation: "Space radiation",
  isolation: "Isolation and confinement",
  distance: "Distance from Earth",
  gravity: "Altered gravity",
  hostile_environment: "Hostile, closed environment",
} as const satisfies Record<Schemas["Hazard"], string>;

export const ROLE_LABEL = {
  astronaut: "Astronaut",
  cmo: "Crew medical officer",
  earth: "Earth doctor",
} as const satisfies Record<Schemas["Role"], string>;
