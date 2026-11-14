"use client";
/**
 * Corpul interactiv: o figură umană din particule, în 3D, cu cele patru zone luminate în culoarea stării lor și
 * câte o etichetă pe zonă. Etichetele sunt butoanele (se folosesc și de la tastatură); zonele de pe corp sunt o
 * scurtătură pentru mouse. Starea vine de la backend (`PillarSummary.status`); aici doar se desenează.
 *
 * Norul de particule e în `cloud.ts`, desenarea unui cadru în `renderer.ts`. Aici e scena: mărimile, legănatul,
 * urmărirea cursorului și liniile care leagă fiecare organ de eticheta lui.
 */
import { useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent, type ReactElement } from "react";
import { StatusBadge, cx } from "@/components/ui";
import type { Schemas } from "@/lib/api";
import { useElementWidth, useLatest } from "@/lib/hooks";
import { PILLAR_META, PILLAR_ORDER, TOPIC_META, type Pillar, type Status } from "@/lib/status";
import { getBodyCloud, type BodyCloud } from "./cloud";
import { FULL_TURN, HALF } from "./math3";
import { createBodyRenderer, type BodyView, type Point } from "./renderer";

type PillarSummary = Schemas["PillarSummary"];

interface BodyFigureProps {
  readonly pillars: readonly PillarSummary[];
  /** Zona al cărei panou e deschis. */
  readonly selected: Pillar | null;
  readonly onSelect: (pillar: Pillar) => void;
}

// scena, în px CSS: lată (figura la mijloc, etichetele pe margini) sau îngustă (doar figura, etichetele dedesubt)
const STAGE_HEIGHT = 560;
const STAGE_WIDE = 624;
const STAGE_NARROW = 360;
const BODY_HEIGHT = 500;
const GROUND_Y = 522;
const CARD_WIDTH = 196;
const CARD_HEIGHT = 88;
const CARD_GAP = 6;

// o zonă în limite luminează mai stins decât una în alertă: privirea merge întâi la problemă
const STRENGTH_OK = 0.62;
const STRENGTH_WATCH = 0.92;
const STRENGTH_UNKNOWN = 0.5;
const IDLE_DIM = 0.8;
const STRENGTH = { ok: STRENGTH_OK, watch: STRENGTH_WATCH, alert: 1, unknown: STRENGTH_UNKNOWN } as const satisfies Record<Status, number>;

// mișcarea: corpul se leagănă încet și se întoarce puțin după cursor
const SWAY_ANGLE = 0.42;
const SWAY_PERIOD_MS = 16000;
const POINTER_YAW = 0.55;
const POINTER_PITCH = 0.06;
const BASE_PITCH = 0.13;
const FOLLOW = 0.07;
const CREAM = "rgb(255 247 234)";

/** Unde stă eticheta fiecărei zone pe scena lată: pe ce margine și la ce înălțime (px de sus). */
const BRAIN_CARD_TOP = 8;
const IMMUNE_CARD_TOP = 112;
const HEART_CARD_TOP = 110;
const BONES_CARD_TOP = 286;
const CARD_PLACE = {
  behavioral: { side: "left", top: BRAIN_CARD_TOP },
  immune: { side: "left", top: IMMUNE_CARD_TOP },
  cardio: { side: "right", top: HEART_CARD_TOP },
  musculoskeletal: { side: "right", top: BONES_CARD_TOP },
} as const satisfies Record<Pillar, { readonly side: "left" | "right"; readonly top: number }>;

/** Punctul de pe marginea etichetei în care ajunge linia organului ei. */
const LEADER_ENDS = Object.fromEntries(
  PILLAR_ORDER.map((pillar) => {
    const { side, top } = CARD_PLACE[pillar];
    const x = side === "left" ? CARD_WIDTH + CARD_GAP : STAGE_WIDE - CARD_WIDTH - CARD_GAP;
    return [pillar, { x, y: top + CARD_HEIGHT * HALF }];
  }),
  // `Object.fromEntries` întoarce chei `string`; cheile sunt exact cei patru piloni
) as Readonly<Record<Pillar, Point>>;

/** Zona de pe corp care deschide panoul la clic (doar pentru mouse; tastatura folosește etichetele). */
const HIT_SPOT = {
  behavioral: "left-[90px] top-[14px] h-[92px] w-[80px]",
  cardio: "left-[112px] top-[126px] h-[58px] w-[58px]",
  immune: "left-[72px] top-[186px] h-[106px] w-[116px]",
  musculoskeletal: "left-[78px] top-[294px] h-[236px] w-[104px]",
} as const satisfies Record<Pillar, string>;

const statusColor = (canvas: HTMLCanvasElement, status: Status): string =>
  status === "unknown" ? CREAM : getComputedStyle(canvas).getPropertyValue(`--color-${status}`).trim() || CREAM;

function ZoneCard({ summary, active, onSelect, onHover, className, style }: {
  readonly summary: PillarSummary;
  readonly active: boolean;
  readonly onSelect: () => void;
  readonly onHover: (hovering: boolean) => void;
  readonly className?: string;
  readonly style?: CSSProperties;
}): ReactElement {
  const meta = PILLAR_META[summary.pillar];
  // numele pilonului din interfață (în engleză); `summary.name` vine de la backend, în română
  const name = TOPIC_META[summary.pillar].label;
  return (
    <button
      type="button"
      onClick={onSelect}
      onPointerEnter={() => onHover(true)}
      onPointerLeave={() => onHover(false)}
      onFocus={() => onHover(true)}
      onBlur={() => onHover(false)}
      style={style}
      className={cx(
        "flex h-[88px] flex-col justify-between rounded-2xl border p-3 text-left transition-colors duration-200",
        active ? "border-line-4 bg-white/[0.07]" : "border-line-2 bg-surface/80 hover:border-line-3 hover:bg-white/[0.05]",
        className,
      )}
    >
      <span className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2 text-body font-medium text-fg">
          <meta.icon size={15} strokeWidth={1.8} className="shrink-0 text-fg-3" />
          <span className="truncate">{name}</span>
        </span>
        <StatusBadge status={summary.status} compact />
      </span>
      <span className="line-clamp-2 text-small leading-snug text-fg-3">{summary.headline}</span>
      <span className="sr-only">{`${meta.zone}. Open details.`}</span>
    </button>
  );
}

interface Scene {
  readonly statuses: Readonly<Record<Pillar, Status>>;
  readonly active: Pillar | null;
  readonly wide: boolean;
}

/** Tot ce trebuie pentru un cadru, din starea scenei și din mișcarea curentă. */
function viewOf(canvas: HTMLCanvasElement, scene: Scene, time: number, yaw: number, pitch: number, moving: boolean): BodyView {
  const { statuses, active, wide } = scene;
  const of = <TValue,>(pick: (pillar: Pillar) => TValue): Record<Pillar, TValue> => ({
    behavioral: pick("behavioral"),
    cardio: pick("cardio"),
    immune: pick("immune"),
    musculoskeletal: pick("musculoskeletal"),
  });
  const width = wide ? STAGE_WIDE : STAGE_NARROW;
  return {
    width,
    height: STAGE_HEIGHT,
    axisX: width * HALF,
    groundY: GROUND_Y,
    bodyHeight: BODY_HEIGHT,
    time,
    yaw,
    pitch,
    colors: of((pillar) => statusColor(canvas, statuses[pillar])),
    strengths: of((pillar) => STRENGTH[statuses[pillar]] * (active === null || active === pillar ? 1 : IDLE_DIM)),
    alerting: of((pillar) => statuses[pillar] === "alert"),
    active,
    leaders: wide ? LEADER_ENDS : null,
    moving,
  };
}

export function BodyFigure({ pillars, selected, onSelect }: BodyFigureProps): ReactElement {
  const [wrapRef, width] = useElementWidth<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointer = useRef({ x: 0, y: 0 });
  const [cloud, setCloud] = useState<BodyCloud | null>(null);
  const [hovered, setHovered] = useState<Pillar | null>(null);
  const wide = width >= STAGE_WIDE;
  const active = hovered ?? selected;

  const statuses = useMemo<Record<Pillar, Status>>(() => {
    const of = (pillar: Pillar): Status => pillars.find((summary) => summary.pillar === pillar)?.status ?? "unknown";
    return { behavioral: of("behavioral"), cardio: of("cardio"), immune: of("immune"), musculoskeletal: of("musculoskeletal") };
  }, [pillars]);
  const scene = useLatest<Scene>(useMemo(() => ({ statuses, active, wide }), [statuses, active, wide]));

  // norul se calculează după prima pictare a ecranului, ca pagina să apară imediat
  useEffect(() => {
    const timer = setTimeout(() => setCloud(getBodyCloud()), 0);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cloud) return undefined;
    const paint = createBodyRenderer(canvas, cloud);
    if (!paint) return undefined;
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)");
    const state = { frame: 0, start: 0, yaw: 0, pitch: BASE_PITCH, onScreen: true, painted: null as Scene | null };
    const watcher = new IntersectionObserver(([entry]) => {
      state.onScreen = entry?.isIntersecting ?? true;
    });
    watcher.observe(canvas);

    const tick = (now: number): void => {
      state.frame = requestAnimationFrame(tick);
      if (!state.onScreen) return;
      const current = scene.current;
      if (calm.matches) {
        // fără mișcare: un singur cadru, din față, repictat doar când se schimbă ceva
        if (state.painted !== current) paint(viewOf(canvas, current, 0, 0, BASE_PITCH, false));
        state.painted = current;
        return;
      }
      state.start ||= now;
      const time = now - state.start;
      const sway = Math.sin((time / SWAY_PERIOD_MS) * FULL_TURN) * SWAY_ANGLE;
      state.yaw += (sway + pointer.current.x * POINTER_YAW - state.yaw) * FOLLOW;
      state.pitch += (BASE_PITCH + pointer.current.y * POINTER_PITCH - state.pitch) * FOLLOW;
      paint(viewOf(canvas, current, time, state.yaw, state.pitch, true));
    };
    state.frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(state.frame);
      watcher.disconnect();
    };
  }, [cloud, scene]);

  const onPointerMove = (event: PointerEvent<HTMLDivElement>): void => {
    const box = event.currentTarget.getBoundingClientRect();
    pointer.current = { x: ((event.clientX - box.left) / box.width - HALF) / HALF, y: ((event.clientY - box.top) / box.height - HALF) / HALF };
  };
  const onPointerLeave = (): void => {
    pointer.current = { x: 0, y: 0 };
  };

  const ordered = PILLAR_ORDER.map((pillar) => pillars.find((summary) => summary.pillar === pillar)).filter((summary): summary is PillarSummary => Boolean(summary));

  return (
    <div ref={wrapRef} className="w-full">
      <div onPointerMove={onPointerMove} onPointerLeave={onPointerLeave} className={cx("relative mx-auto h-[560px]", wide ? "w-[624px]" : "w-[360px]")}>
        <canvas ref={canvasRef} aria-hidden="true" className={cx("absolute left-0 top-0 h-[560px]", wide ? "w-[624px]" : "w-[360px]")} />
        <div aria-hidden="true" className={cx("absolute top-0 h-[560px] w-[260px]", wide ? "left-[182px]" : "left-[50px]")}>
          {ordered.map((summary) => (
            <button
              key={summary.pillar}
              type="button"
              tabIndex={-1}
              onClick={() => onSelect(summary.pillar)}
              onPointerEnter={() => setHovered(summary.pillar)}
              onPointerLeave={() => setHovered(null)}
              className={cx("absolute cursor-pointer rounded-full", HIT_SPOT[summary.pillar])}
            />
          ))}
        </div>
        {wide &&
          ordered.map((summary) => (
            <ZoneCard
              key={summary.pillar}
              summary={summary}
              active={active === summary.pillar}
              onSelect={() => onSelect(summary.pillar)}
              onHover={(hovering) => setHovered(hovering ? summary.pillar : null)}
              className={cx("absolute w-[196px]", CARD_PLACE[summary.pillar].side === "left" ? "left-0" : "right-0")}
              style={{ top: CARD_PLACE[summary.pillar].top }}
            />
          ))}
      </div>
      {!wide && (
        <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
          {ordered.map((summary) => (
            <ZoneCard
              key={summary.pillar}
              summary={summary}
              active={active === summary.pillar}
              onSelect={() => onSelect(summary.pillar)}
              onHover={(hovering) => setHovered(hovering ? summary.pillar : null)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
