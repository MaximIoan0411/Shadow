"use client";
/**
 * Gaura neagră de pe ecranul de intrare: o imagine vie, fără date. Camera se apropie încet la apariție, apoi
 * plutește în jurul găurii și se înclină puțin după cursor; discul de acreție se rotește.
 *
 * Desenul e în `blackholeGl.ts` (WebGL2) și `blackholeShaders.ts`. Aici e scena: camera, mărimea pânzei și
 * calitatea, care scade singură dacă placa video nu ține ritmul. Fără WebGL2 se arată o imagine fixă din CSS;
 * cu „reduce motion” se desenează un singur cadru, la calitate maximă.
 */
import { useEffect, useRef, useState, type ReactElement } from "react";
import { HALF, add, cross, normalize, scale, sub, type Vec3 } from "@/components/body/math3";
import { cx } from "@/components/ui";
import { createBlackHoleRenderer, type BlackHoleFrame } from "./blackholeGl";

// camera, în raze ale orizontului: distanța, cât de sus stă față de planul discului, cât e rotită în jurul privirii
const DISTANCE = 24;
const INCLINATION = 0.105;
const ROLL = -0.21;
const AZIMUTH = 0.6;
const DRIFT_PER_SECOND = 0.012;
// la apariție camera pornește de mai departe și se apropie
const DOLLY = 11;
const DOLLY_SECONDS = 2.4;
const FADE_SECONDS = 1.8;
// cât urmărește cursorul
const POINTER_AZIMUTH = 0.16;
const POINTER_INCLINATION = 0.045;
const FOLLOW = 0.04;
// încadrarea: discul ocupă cam 80% din lățimea scenei (dar nu mai mult decât îi permite înălțimea)
const DISK_RADIUS = 11.5;
const FIT = 0.44;
const MAX_ASPECT = 1.3;
/** Unde stă gaura pe scenă (0–1, y în sus): la mijloc pe lățime, puțin deasupra mijlocului pe înălțime. */
const CENTER_X = 0.5;
const CENTER_Y = 0.56;
const CENTER: readonly [number, number] = [CENTER_X, CENTER_Y];
const UP: Vec3 = [0, 1, 0];

// calitatea: ce parte din pixeli se desenează; scade dacă două ferestre de cadre la rând ies lente
const MAX_PIXEL_RATIO = 1.5;
const QUALITY_START = 0.7;
const QUALITY_MIN = 0.4;
const QUALITY_DOWN = 0.82;
const QUALITY_UP = 1.12;
const WARMUP_FRAMES = 30;
const WINDOW_FRAMES = 40;
const SLOW_MS = 22;
const FAST_MS = 18.5;
const SLOW_WINDOWS = 2;
const PAUSE_MS = 250;
const MS_PER_SECOND = 1000;
/** Momentul desenat când nu e mișcare: camera e deja așezată. */
const STILL_SECONDS = 40;

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

/** Cadrul de la un moment dat: unde e camera și încotro privește. */
function frameAt(seconds: number, turn: number, tilt: number, aspect: number): BlackHoleFrame {
  const azimuth = AZIMUTH + seconds * DRIFT_PER_SECOND + turn;
  const inclination = INCLINATION + tilt;
  const distance = DISTANCE + DOLLY * Math.exp(-seconds / DOLLY_SECONDS);
  const camera: Vec3 = [distance * Math.cos(inclination) * Math.sin(azimuth), distance * Math.sin(inclination), distance * Math.cos(inclination) * Math.cos(azimuth)];
  const forward = normalize(scale(camera, -1));
  const level = normalize(cross(forward, UP));
  const above = cross(level, forward);
  const right = add(scale(level, Math.cos(ROLL)), scale(above, Math.sin(ROLL)));
  const up = sub(scale(above, Math.cos(ROLL)), scale(level, Math.sin(ROLL)));
  return {
    time: seconds,
    camera,
    view: Float32Array.from([...right, ...up, ...forward]),
    focal: (FIT * Math.min(aspect, MAX_ASPECT) * DISTANCE) / DISK_RADIUS,
    center: CENTER,
    fade: clamp01(seconds / FADE_SECONDS),
  };
}

export function BlackHole({ className }: { readonly className?: string }): ReactElement {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const box = boxRef.current;
    const canvas = canvasRef.current;
    if (!box || !canvas) return undefined;
    const renderer = createBlackHoleRenderer(canvas);
    if (!renderer) {
      setFailed(true);
      return undefined;
    }
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)");
    const state = { frame: 0, start: 0, last: 0, width: 0, height: 0, sized: false, pointerX: 0, pointerY: 0, turn: 0, tilt: 0, quality: QUALITY_START, ceiling: 1, counted: 0, spent: 0, seen: 0, slow: 0 };

    const fit = (): void => {
      if (!state.width || !state.height) return;
      const ratio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
      renderer.resize(Math.round(state.width * ratio), Math.round(state.height * ratio), calm.matches ? 1 : state.quality);
      state.sized = true;
    };
    const still = (): void => {
      if (state.sized) renderer.render(frameAt(STILL_SECONDS, 0, 0, state.width / state.height));
    };
    const sizer = new ResizeObserver(([entry]) => {
      state.width = Math.round(entry?.contentRect.width ?? 0);
      state.height = Math.round(entry?.contentRect.height ?? 0);
      fit();
      if (calm.matches) still();
    });
    sizer.observe(box);

    const onPointer = (event: PointerEvent): void => {
      state.pointerX = (event.clientX / window.innerWidth - HALF) / HALF;
      state.pointerY = (event.clientY / window.innerHeight - HALF) / HALF;
    };
    const onLost = (event: Event): void => {
      event.preventDefault();
      setFailed(true);
    };
    window.addEventListener("pointermove", onPointer);
    canvas.addEventListener("webglcontextlost", onLost);

    /** Ține socoteala duratei cadrelor și schimbă rezoluția scenei când placa video nu ține ritmul (sau are rezervă). */
    const tune = (delta: number): void => {
      state.seen += 1;
      if (state.seen <= WARMUP_FRAMES || delta > PAUSE_MS) return;
      state.counted += 1;
      state.spent += delta;
      if (state.counted < WINDOW_FRAMES) return;
      const average = state.spent / state.counted;
      state.counted = 0;
      state.spent = 0;
      state.slow = average > SLOW_MS ? state.slow + 1 : 0;
      if (state.slow >= SLOW_WINDOWS && state.quality > QUALITY_MIN) {
        state.quality = Math.max(QUALITY_MIN, state.quality * QUALITY_DOWN);
        state.ceiling = state.quality;
        state.slow = 0;
        fit();
      } else if (average < FAST_MS && state.quality < state.ceiling) {
        state.quality = Math.min(state.ceiling, state.quality * QUALITY_UP);
        fit();
      }
    };

    const tick = (now: number): void => {
      if (calm.matches) return;
      state.frame = requestAnimationFrame(tick);
      if (!state.sized) return;
      state.start ||= now;
      tune(now - (state.last || now));
      state.last = now;
      state.turn += (state.pointerX * POINTER_AZIMUTH - state.turn) * FOLLOW;
      state.tilt += (state.pointerY * POINTER_INCLINATION - state.tilt) * FOLLOW;
      renderer.render(frameAt((now - state.start) / MS_PER_SECOND, state.turn, state.tilt, state.width / state.height));
    };
    state.frame = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(state.frame);
      sizer.disconnect();
      window.removeEventListener("pointermove", onPointer);
      canvas.removeEventListener("webglcontextlost", onLost);
      renderer.dispose();
    };
  }, []);

  return (
    <div ref={boxRef} aria-hidden="true" className={cx("bg-black", className)}>
      <canvas ref={canvasRef} className={cx("block h-full w-full", failed && "hidden")} />
      {failed && <div className="blackhole-still absolute inset-0" />}
    </div>
  );
}
