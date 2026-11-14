/**
 * Nuanțele SHADOW, după modelul Quaternion: fiecare ecran are trei nuanțe (aurora, orb, inelul AI-ului),
 * fiecare pilon are culoarea lui, iar fiecare stare are culoare + formă + cuvânt.
 */
import type { CSSProperties } from "react";
import type { components } from "./shadow-api";

type Status = components["schemas"]["Status"];
type Pillar = components["schemas"]["Pillar"];

/** Trei nuanțe pe ecran: a = valul principal, b = a doua culoare, c = lumina care plutește. */
export type ScreenHues = { readonly a: string; readonly b: string; readonly c: string };

export const SCREEN_HUES = {
  login: { a: "var(--color-steel)", b: "var(--color-periwinkle)", c: "var(--color-cyan)" },
  dashboard: { a: "var(--color-periwinkle)", b: "var(--color-violet)", c: "var(--color-cyan)" },
  checkin: { a: "var(--color-mint)", b: "#3fb6d9", c: "var(--color-cyan)" },
  pvt: { a: "var(--color-violet)", b: "var(--color-periwinkle)", c: "var(--color-orchid)" },
  alerts: { a: "var(--color-coral)", b: "var(--color-violet)", c: "var(--color-amber)" },
  cmo: { a: "var(--color-violet)", b: "var(--color-periwinkle)", c: "var(--color-mint)" },
  evidence: { a: "var(--color-steel)", b: "var(--color-mint)", c: "var(--color-periwinkle)" },
  /** Pământul: portocaliul distanței (singurul ecran cu portocaliu, ca în mockup). */
  missionControl: { a: "var(--color-amber)", b: "var(--color-coral)", c: "var(--color-orchid)" },
  /** Furtuna solară: suprascrie ecranul curent cât timp e activă. */
  storm: { a: "var(--color-danger)", b: "var(--color-amber)", c: "var(--color-coral)" },
} as const satisfies Record<string, ScreenHues>;

export type Screen = keyof typeof SCREEN_HUES;

/** Stilul de pus pe rădăcina unui ecran: `<div style={hueStyle("dashboard")}>`. */
export const hueStyle = (screen: Screen): CSSProperties =>
  ({ "--hue-a": SCREEN_HUES[screen].a, "--hue-b": SCREEN_HUES[screen].b, "--hue-c": SCREEN_HUES[screen].c }) as CSSProperties;

export const PILLAR_HUE: Readonly<Record<Pillar, string>> = {
  behavioral: "var(--color-pillar-behavioral)",
  cardio: "var(--color-pillar-cardio)",
  immune: "var(--color-pillar-immune)",
  musculoskeletal: "var(--color-pillar-musculoskeletal)",
};

/** Culoarea nu apare niciodată singură: mereu cu forma și cuvântul de aici. */
export const STATUS_META: Readonly<Record<Status, { readonly color: string; readonly shape: string; readonly label: string }>> = {
  ok: { color: "var(--color-status-ok)", shape: "●", label: "În limite" },
  watch: { color: "var(--color-status-watch)", shape: "▲", label: "De urmărit" },
  alert: { color: "var(--color-status-alert)", shape: "■", label: "Alertă" },
  unknown: { color: "var(--color-status-unknown)", shape: "○", label: "Fără date" },
};
