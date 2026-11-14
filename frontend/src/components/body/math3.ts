/* eslint-disable ts-patterns/no-magic-numbers -- formule de geometrie: numerele sunt coeficienții lor (mulberry32, Catmull-Rom, distanțe semnate) */
/**
 * Geometria din spatele corpului din particule: vectori, un generator de numere cu sămânță (figura iese la fel
 * de fiecare dată), curbe netede prin puncte și câmpuri de distanță (cât de departe e un punct de o formă;
 * negativ = înăuntru). Formele se unesc lin cu `smoothMin`, ca umărul să curgă în braț fără muchie.
 */

export type Vec3 = readonly [number, number, number];

export const add = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const scale = (a: Vec3, k: number): Vec3 => [a[0] * k, a[1] * k, a[2] * k];
export const dot = (a: Vec3, b: Vec3): number => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a: Vec3, b: Vec3): Vec3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const norm = (a: Vec3): number => Math.hypot(a[0], a[1], a[2]);
export const distance = (a: Vec3, b: Vec3): number => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
export const mirrorX = (a: Vec3): Vec3 => [-a[0], a[1], a[2]];

const TINY = 1e-9;
export const HALF = 0.5;
export const FULL_TURN = Math.PI * 2;
/** Fără normală: particulă din interior, nu de pe piele. */
export const NO_NORMAL: Vec3 = [0, 0, 0];

export function normalize(a: Vec3): Vec3 {
  const length = norm(a);
  return length < TINY ? [0, 1, 0] : scale(a, 1 / length);
}

/** Generator de numere pseudo-aleatoare cu sămânță (mulberry32): aceeași sămânță, același șir. */
export function seededRandom(seed: number): () => number {
  const state = { value: seed >>> 0 };
  return () => {
    state.value = (state.value + 0x6d2b79f5) >>> 0;
    const mixed = Math.imul(state.value ^ (state.value >>> 15), state.value | 1);
    const again = mixed ^ (mixed + Math.imul(mixed ^ (mixed >>> 7), mixed | 61));
    return ((again ^ (again >>> 14)) >>> 0) / 4294967296;
  };
}

/** O direcție la întâmplare, uniformă pe sferă. */
export function randomDirection(random: () => number): Vec3 {
  const height = random() * 2 - 1;
  const angle = random() * Math.PI * 2;
  const ring = Math.sqrt(Math.max(0, 1 - height * height));
  return [ring * Math.cos(angle), height, ring * Math.sin(angle)];
}

/** Rotește un punct în jurul axei Z (înclinarea unei forme în planul din față). */
export function tiltZ(point: Vec3, angle: number): Vec3 {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return [point[0] * cos - point[1] * sin, point[0] * sin + point[1] * cos, point[2]];
}

/** Punctul de pe curba netedă (Catmull-Rom) care trece prin `points`, la `t` între 0 și 1. */
export function alongCurve(points: readonly Vec3[], t: number): Vec3 {
  const last = points.length - 1;
  const first = points[0] ?? [0, 0, 0];
  if (last < 1) return first;
  const position = Math.min(Math.max(t, 0), 1) * last;
  const index = Math.min(Math.floor(position), last - 1);
  const u = position - index;
  const at = (i: number): Vec3 => points[Math.min(Math.max(i, 0), last)] ?? first;
  const [p0, p1, p2, p3] = [at(index - 1), at(index), at(index + 1), at(index + 2)];
  const blend = (axis: 0 | 1 | 2): number =>
    0.5 * (2 * p1[axis] + (p2[axis] - p0[axis]) * u + (2 * p0[axis] - 5 * p1[axis] + 4 * p2[axis] - p3[axis]) * u * u + (3 * p1[axis] - p0[axis] - 3 * p2[axis] + p3[axis]) * u * u * u);
  return [blend(0), blend(1), blend(2)];
}

/** Direcția curbei la `t`. */
export function curveTangent(points: readonly Vec3[], t: number): Vec3 {
  const step = 0.01;
  return normalize(sub(alongCurve(points, Math.min(1, t + step)), alongCurve(points, Math.max(0, t - step))));
}

/** Doi vectori perpendiculari pe `tangent` și între ei: reperul în jurul unei curbe. */
export function frameAround(tangent: Vec3): readonly [Vec3, Vec3] {
  const helper: Vec3 = Math.abs(tangent[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0];
  const side = normalize(cross(tangent, helper));
  return [side, normalize(cross(tangent, side))];
}

/** Valoarea interpolată liniar dintr-o listă, la `t` între 0 și 1 (raza unui os de-a lungul lui). */
export function sampleProfile(values: readonly number[], t: number): number {
  const last = values.length - 1;
  const position = Math.min(Math.max(t, 0), 1) * last;
  const index = Math.min(Math.floor(position), Math.max(last - 1, 0));
  const from = values[index] ?? 0;
  const to = values[index + 1] ?? from;
  return from + (to - from) * (position - index);
}

// ---------------------------------------------------------------- câmpuri de distanță

/** Distanța semnată de la un punct la o formă: negativă înăuntru, zero pe suprafață. */
export type Field = (x: number, y: number, z: number) => number;

/** Unirea lină a două forme: `k` e lățimea racordului dintre ele. */
export function smoothMin(a: number, b: number, k: number): number {
  const h = Math.max(k - Math.abs(a - b), 0) / k;
  return Math.min(a, b) - h * h * k * 0.25;
}

/** Elipsoid cu centrul `c` și razele `r`, opțional înclinat în jurul axei Z. */
export function ellipsoidField(c: Vec3, r: Vec3, tilt = 0): Field {
  const cos = Math.cos(tilt);
  const sin = Math.sin(tilt);
  const smallest = Math.min(r[0], r[1], r[2]);
  return (x, y, z) => {
    const dx = x - c[0];
    const dy = y - c[1];
    const px = (dx * cos + dy * sin) / r[0];
    const py = (dy * cos - dx * sin) / r[1];
    const pz = (z - c[2]) / r[2];
    const k0 = Math.hypot(px, py, pz);
    const k1 = Math.hypot(px / r[0], py / r[1], pz / r[2]);
    return k1 < TINY ? -smallest : (k0 * (k0 - 1)) / k1;
  };
}

/** Con rotunjit între `a` (raza `ra`) și `b` (raza `rb`): un segment de braț sau de picior. */
export function coneField(a: Vec3, b: Vec3, ra: number, rb: number): Field {
  const ba = sub(b, a);
  const l2 = dot(ba, ba);
  const rr = ra - rb;
  const a2 = l2 - rr * rr;
  const il2 = 1 / l2;
  return (x, y, z) => {
    const pa: Vec3 = [x - a[0], y - a[1], z - a[2]];
    const along = dot(pa, ba);
    const past = along - l2;
    const across = sub(scale(pa, l2), scale(ba, along));
    const x2 = dot(across, across);
    const y2 = along * along * l2;
    const z2 = past * past * l2;
    const k = Math.sign(rr) * rr * rr * x2;
    if (Math.sign(past) * a2 * z2 > k) return Math.sqrt(x2 + z2) * il2 - rb;
    if (Math.sign(along) * a2 * y2 < k) return Math.sqrt(x2 + y2) * il2 - ra;
    return (Math.sqrt(x2 * a2 * il2) + along * rr) * il2 - ra;
  };
}

/** Direcția în care câmpul crește cel mai repede: normala suprafeței în acel punct. */
export function fieldNormal(field: Field, point: Vec3, value: number): Vec3 {
  const step = 0.0015;
  const [x, y, z] = point;
  return normalize([field(x + step, y, z) - value, field(x, y + step, z) - value, field(x, y, z + step) - value]);
}
