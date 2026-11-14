/**
 * Desenează norul corpului pe o pânză 2D, cadru cu cadru.
 *
 * Pielea e „de sticlă”: particulele ei luminează la margini (unde suprafața se întoarce de la privitor) și abia se
 * văd în față, așa că organele dinăuntru rămân la vedere. Nodurile de pe piele sunt legate într-o rețea de linii
 * fine, iar o ceață slabă dă corpului volum. Organele iau culoarea stării lor; coloana și nervii rămân crem.
 * Luminile se adună: unde particulele sunt dese, figura strălucește.
 *
 * Particulele (peste zece mii) nu se pictează cu API-ul pânzei, care ar fi prea lent fără placă video: lumina
 * fiecăreia se împarte între cei patru pixeli din jurul ei, într-un tampon care se pune pe pânză o singură dată pe
 * cadru. Liniile, luminile din jurul organelor și liniile spre etichete sunt puține și se trag cu API-ul obișnuit.
 *
 * Mișcarea: corpul se așază din praf la apariție, apoi se leagănă încet; inima bate, prin nervi și vase trec unde,
 * o bandă de lumină urcă din când în când pe corp. Cu „reduce motion”, se desenează un singur cadru, nemișcat.
 */
import { PILLAR_ORDER, type Pillar } from "@/lib/status";
import { HEART_CENTER } from "./anatomy";
import { GROUP, GROUP_COUNT, NO_FLOW, PILLAR_GROUP, type BodyCloud } from "./cloud";
import { FULL_TURN, HALF, type Vec3 } from "./math3";

export interface Point {
  readonly x: number;
  readonly y: number;
}

export interface BodyView {
  /** Mărimea pânzei, în px CSS. */
  readonly width: number;
  readonly height: number;
  /** Axa corpului (x), linia tălpilor (y) și înălțimea corpului, în px CSS. */
  readonly axisX: number;
  readonly groundY: number;
  readonly bodyHeight: number;
  /** Milisecunde de la apariția figurii. */
  readonly time: number;
  /** Rotația în jurul axei verticale și aplecarea spre privitor, în radiani. */
  readonly yaw: number;
  readonly pitch: number;
  readonly colors: Readonly<Record<Pillar, string>>;
  /** Cât de tare luminează fiecare zonă (0–1), după stare și după zona activă. */
  readonly strengths: Readonly<Record<Pillar, number>>;
  readonly alerting: Readonly<Record<Pillar, boolean>>;
  readonly active: Pillar | null;
  /** Unde se prinde linia fiecărei zone de eticheta ei; `null` când etichetele stau sub figură. */
  readonly leaders: Readonly<Record<Pillar, Point>> | null;
  readonly moving: boolean;
}

type Rgb = readonly [number, number, number];

const CREAM = "rgb(255 247 234)";
const WHITE_RGB: Rgb = [1, 1, 1];
const AXES = 3;
const Y_AXIS = 1;
const Z_AXIS = 2;
const RGB = 3;
const RGBA = 4;
const GREEN = 1;
const BLUE = 2;
const ALPHA = 3;
const BYTE = 255;
const HEX = 16;
const RED_SHIFT = 16;
const GREEN_SHIFT = 8;
const MAX_PIXEL_RATIO = 2;
const SQUARE = 2;
const MS_PER_SECOND = 1000;

// camera
const CAMERA_DISTANCE = 3.2;
const PIVOT_HEIGHT = 0.5;
const DEPTH_FADE = 1.6;

// pielea
const SKIN_BASE = 0.1;
const SKIN_RIM = 0.82;
const SKIN_BACK = 0.42;
const NODE_BASE = 0.1;
const NODE_GAIN = 1.15;
const TWINKLE_DEPTH = 0.3;
const TWINKLE_SPEED = 0.27;
const LINE_GAIN = 0.5;
const LINE_WIDTH = 0.6;
const LINE_BUCKETS = 6;
const FAINT = 0.02;

// interiorul
const NERVE_ALPHA = 0.36;
const NERVE_WAVE = 0.85;
const NERVE_SPEED = 0.55;
const GROUND_ALPHA = 0.32;
const ORGAN_ALPHA = 0.85;
const ORGAN_FLICKER = 0.45;
const ORGAN_FLICKER_SPEED = 0.37;
const ORGAN_LINE_GAIN = 0.5;
const FLOW_SPEED = 1;
const FLOW_GAIN = 0.9;
const WAVE_WIDTH = 0.22;
const HALO_ALPHA = 0.2;
const HALO_ALERT_GAIN = 1.5;
const TRANSPARENT_SUFFIX = "00";

// mărimea particulelor, în px CSS
const DUST_SIZE = 1.2;
const NODE_SIZE = 1.7;
const NERVE_SIZE = 1.2;
const GROUND_SIZE = 1.5;
const ORGAN_SIZE = 1.55;

// tamponul de pixeli: lumina peste 1 se albește puțin, ca miezul unei zone dese să „ardă”
const WHITEN = 0.22;
const TINY = 1e-6;
/** Cu cât crește lumina unei particule pe ecrane dese (0 = deloc, 2 = aceeași lumină totală ca pe un ecran obișnuit). */
const DENSITY_GAIN = 1.5;

// ceața: densitatea pielii pe o grilă rară, netezită și întinsă peste figură
const FOG_CELL = 8;
const FOG_GAIN = 0.0125;
const FOG_BLUR = [-1, 0, 1] as const;
const FOG_BLUR_CELLS = 9;
const GLOW_SPRITE_PX = 64;
const FLOOR_GLOW_WIDTH = 0.34;
const FLOOR_GLOW_ALPHA = 0.16;
const FLOOR_FLATTEN = 1.6;

// bătaia inimii: două lovituri apropiate, apoi pauză
const BEAT_PERIOD_MS = 1050;
const BEAT_FIRST = 0.1;
const BEAT_SECOND = 0.32;
const BEAT_SHARPNESS = 0.06;
const BEAT_SECOND_GAIN = 0.6;
const BEAT_SWELL = 0.085;

// zona în alertă „respiră”
const PULSE_BASE = 0.78;
const PULSE_DEPTH = 0.22;
const PULSE_PERIOD_MS = 2400;

// banda de lumină care urcă pe corp
const SCAN_EVERY_MS = 9000;
const SCAN_TRAVEL_MS = 2600;
const SCAN_START_MS = 2600;
const SCAN_WIDTH = 0.055;
const SCAN_GAIN = 0.8;
/** Cât din banda de lumină prinde și pe particulele din față, nu doar pe cele de la margine. */
const SCAN_FLAT = 0.3;
// inelul scanerului: o elipsă subțire în jurul corpului, la înălțimea benzii
const SCAN_RING_RADIUS = 0.2;
const SCAN_RING_ALPHA = 0.4;
const SCAN_MARGIN = 0.06;
const SCAN_AWAY = -9;

// apariția: particulele se strâng din praf, de jos în sus
const INTRO_MS = 1900;
const INTRO_RISE = 0.5;
const INTRO_SCATTER = 0.2;
const INTRO_SPAN = 0.3;
/** Când toate particulele sunt la locul lor (în fracțiuni din `INTRO_MS`) și valoarea folosită pentru cadrul nemișcat. */
const INTRO_SETTLED = INTRO_RISE + INTRO_SCATTER + INTRO_SPAN;
const INTRO_DONE = 2;
const INTRO_SPREAD = 1.5;
const INTRO_SWIRL = 1.4;
const INTRO_DROP = 0.05;
const CUBIC = 3;
const LINES_FROM = 0.5;
const LINES_SPAN = 0.5;
const GLOW_FROM = 0.8;
const GLOW_SPAN = 0.3;

// liniile spre etichete
const LEADER_ALPHA = 0.3;
const LEADER_ACTIVE_ALPHA = 0.8;
const LEADER_ELBOW = 22;
const ANCHOR_RING = 4.5;
const ANCHOR_DOT = 1.5;

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));
/** Undă în triunghi între 0 și 1, cu perioada 1: o sclipire ieftină, fără sinus. */
const triangle = (phase: number): number => Math.abs(phase - Math.floor(phase) - HALF) / HALF;
const fract = (value: number): number => value - Math.floor(value);
const easeOut = (t: number): number => 1 - (1 - t) ** CUBIC;
const bump = (phase: number, center: number): number => Math.exp(-(((phase - center) / BEAT_SHARPNESS) ** SQUARE));

/** Cât de umflată e inima în acest moment (0–1). */
const heartbeat = (time: number): number => {
  const phase = fract(time / BEAT_PERIOD_MS);
  return bump(phase, BEAT_FIRST) + BEAT_SECOND_GAIN * bump(phase, BEAT_SECOND);
};

/** Creasta unei unde care trece printr-un drum: 1 pe creastă, 0 în rest. */
const crest = (flow: number, travelled: number): number => {
  const behind = fract(travelled - flow);
  return behind < WAVE_WIDTH ? 1 - behind / WAVE_WIDTH : 0;
};

const SIZE_BY_GROUP: readonly number[] = Array.from({ length: GROUP_COUNT }, (_, group) => {
  const sizes: Readonly<Record<number, number>> = { [GROUP.dust]: DUST_SIZE, [GROUP.node]: NODE_SIZE, [GROUP.nerve]: NERVE_SIZE, [GROUP.ground]: GROUND_SIZE };
  return sizes[group] ?? ORGAN_SIZE;
});

const PILLAR_BY_GROUP: readonly (Pillar | null)[] = Array.from({ length: GROUP_COUNT }, (_, group) => PILLAR_ORDER.find((pillar) => PILLAR_GROUP[pillar] === group) ?? null);

/** O pată rotundă crem care se stinge spre margine (lumina de pe podea). */
function softSprite(): HTMLCanvasElement {
  const sprite = document.createElement("canvas");
  sprite.width = GLOW_SPRITE_PX;
  sprite.height = GLOW_SPRITE_PX;
  const brush = sprite.getContext("2d");
  if (!brush) return sprite;
  const middle = GLOW_SPRITE_PX * HALF;
  const fade = brush.createRadialGradient(middle, middle, 0, middle, middle, middle);
  fade.addColorStop(0, "rgb(255 247 234 / 1)");
  fade.addColorStop(1, "rgb(255 247 234 / 0)");
  brush.fillStyle = fade;
  brush.fillRect(0, 0, GLOW_SPRITE_PX, GLOW_SPRITE_PX);
  return sprite;
}

/* eslint-disable ts-patterns/no-param-reassign -- API-ul Canvas 2D e cu stare: culoarea, opacitatea și mărimea pânzei se setează prin atribuire */
/**
 * Pregătește desenarea pe `canvas` și întoarce funcția care pictează un cadru.
 * Întoarce `null` dacă browserul nu dă un context 2D.
 */
export function createBodyRenderer(canvas: HTMLCanvasElement, cloud: BodyCloud): ((view: BodyView) => void) | null {
  const context = canvas.getContext("2d");
  const fogCanvas = document.createElement("canvas");
  const fogBrush = fogCanvas.getContext("2d");
  if (!context || !fogBrush) return null;
  const { position, normal, group: groups, flow: flows, beats, seed: seeds, linkFrom, linkTo } = cloud;
  const screenX = new Float32Array(cloud.count);
  const screenY = new Float32Array(cloud.count);
  const alphas = new Float32Array(cloud.count);
  const glow = softSprite();
  const parsed = new Map<string, Rgb>();
  // tamponul de pixeli în care se adună lumina particulelor, și lista pixelilor atinși (doar ei se șterg și se copiază)
  const raster = { width: 0, height: 0, light: new Float32Array(0), touched: new Uint32Array(0), used: 0, image: null as ImageData | null };
  const fog = { cols: 0, rows: 0, density: new Float32Array(0), image: null as ImageData | null };

  /** Culoarea CSS a unei stări, ca trei numere între 0 și 1. */
  const rgbOf = (color: string): Rgb => {
    const known = parsed.get(color);
    if (known) return known;
    context.fillStyle = color;
    const hex = Number.parseInt(String(context.fillStyle).slice(1), HEX);
    const rgb: Rgb = Number.isNaN(hex) ? WHITE_RGB : [((hex >> RED_SHIFT) & BYTE) / BYTE, ((hex >> GREEN_SHIFT) & BYTE) / BYTE, (hex & BYTE) / BYTE];
    parsed.set(color, rgb);
    return rgb;
  };
  const cream = rgbOf(CREAM);

  // Starea cadrului curent. Funcțiile de mai jos sunt create o singură dată și citesc de aici: așa motorul
  // JavaScript le poate optimiza, ceea ce contează când rulează de peste zece mii de ori pe cadru.
  const now = {
    ratio: 1,
    seconds: 0,
    cosYaw: 1,
    sinYaw: 0,
    cosPitch: 1,
    sinPitch: 0,
    axisX: 0,
    pivotY: 0,
    bodyHeight: 0,
    scanY: SCAN_AWAY,
    pulse: 1,
    swell: 1,
    strengths: { behavioral: 0, cardio: 0, immune: 0, musculoskeletal: 0 } as Readonly<Record<Pillar, number>>,
    alerting: { behavioral: false, cardio: false, immune: false, musculoskeletal: false } as Readonly<Record<Pillar, boolean>>,
    tints: { behavioral: cream, cardio: cream, immune: cream, musculoskeletal: cream } as Readonly<Record<Pillar, Rgb>>,
  };

  const resize = (view: BodyView, ratio: number): void => {
    const width = Math.round(view.width * ratio);
    const height = Math.round(view.height * ratio);
    if (raster.width === width && raster.height === height) return;
    canvas.width = width;
    canvas.height = height;
    raster.width = width;
    raster.height = height;
    raster.light = new Float32Array(width * height * RGB);
    raster.touched = new Uint32Array(width * height);
    raster.used = 0;
    raster.image = context.createImageData(width, height);
    fog.cols = Math.ceil(view.width / FOG_CELL) + 1;
    fog.rows = Math.ceil(view.height / FOG_CELL) + 1;
    fog.density = new Float32Array(fog.cols * fog.rows);
    fog.image = fogBrush.createImageData(fog.cols, fog.rows);
    fogCanvas.width = fog.cols;
    fogCanvas.height = fog.rows;
  };

  /** Din spațiul corpului pe ecran (px CSS); întoarce adâncimea (spre privitor = pozitiv). */
  const project = (x: number, y: number, z: number, cos: number, sin: number, index: number): number => {
    const turnedX = x * cos + z * sin;
    const turnedZ = z * cos - x * sin;
    const lifted = y - PIVOT_HEIGHT;
    const depth = lifted * now.sinPitch + turnedZ * now.cosPitch;
    const zoom = (CAMERA_DISTANCE / (CAMERA_DISTANCE - depth)) * now.bodyHeight;
    screenX[index] = now.axisX + turnedX * zoom;
    screenY[index] = now.pivotY - (lifted * now.cosPitch - turnedZ * now.sinPitch) * zoom;
    return depth;
  };

  /** Adaugă lumină într-un pixel; prima atingere îl trece pe lista celor de copiat pe pânză. */
  const lightUp = (pixel: number, amount: number, tint: Rgb): void => {
    const { light, touched } = raster;
    const at = pixel * RGB;
    const red = light[at] ?? 0;
    const green = light[at + GREEN] ?? 0;
    const blue = light[at + BLUE] ?? 0;
    if (!(red + green + blue) && raster.used < touched.length) {
      touched[raster.used] = pixel;
      raster.used += 1;
    }
    light[at] = red + tint[0] * amount;
    light[at + GREEN] = green + tint[GREEN] * amount;
    light[at + BLUE] = blue + tint[BLUE] * amount;
  };

  /** Împarte lumina unei particule între cei patru pixeli din jurul ei, după cât de aproape e de fiecare. */
  const splat = (x: number, y: number, energy: number, tint: Rgb): void => {
    const fromLeft = x - HALF;
    const fromTop = y - HALF;
    const left = Math.floor(fromLeft);
    const top = Math.floor(fromTop);
    if (left < 0 || top < 0 || left + 1 >= raster.width || top + 1 >= raster.height) return;
    const right = fromLeft - left;
    const down = fromTop - top;
    const pixel = top * raster.width + left;
    lightUp(pixel, (1 - right) * (1 - down) * energy, tint);
    lightUp(pixel + 1, right * (1 - down) * energy, tint);
    lightUp(pixel + raster.width, (1 - right) * down * energy, tint);
    lightUp(pixel + raster.width + 1, right * down * energy, tint);
  };

  /** Adaugă o particulă de piele la ceață: densitatea se împarte între cele patru celule din jur. */
  const thicken = (x: number, y: number, amount: number): void => {
    const column = Math.floor(x / FOG_CELL);
    const row = Math.floor(y / FOG_CELL);
    if (column < 0 || row < 0 || column + 1 >= fog.cols || row + 1 >= fog.rows) return;
    const { density } = fog;
    const right = x / FOG_CELL - column;
    const down = y / FOG_CELL - row;
    const cell = row * fog.cols + column;
    density[cell] = (density[cell] ?? 0) + (1 - right) * (1 - down) * amount;
    density[cell + 1] = (density[cell + 1] ?? 0) + right * (1 - down) * amount;
    density[cell + fog.cols] = (density[cell + fog.cols] ?? 0) + (1 - right) * down * amount;
    density[cell + fog.cols + 1] = (density[cell + fog.cols + 1] ?? 0) + right * down * amount;
  };

  /** Lumina unei particule de pe piele: tare la margine, slabă în față, și mai slabă pe spate. */
  const skinLight = (at: number, seed: number, y: number): number => {
    const turned = (normal[at + Z_AXIS] ?? 0) * now.cosYaw - (normal[at] ?? 0) * now.sinYaw;
    const facing = (normal[at + Y_AXIS] ?? 0) * now.sinPitch + turned * now.cosPitch;
    const rim = 1 - Math.abs(facing);
    const lit = (SKIN_BASE + SKIN_RIM * rim * rim) * (facing < 0 ? SKIN_BACK : 1);
    const twinkle = 1 - TWINKLE_DEPTH * triangle(now.seconds * TWINKLE_SPEED + seed);
    const scan = Math.max(0, 1 - Math.abs(y - now.scanY) / SCAN_WIDTH) * SCAN_GAIN;
    return lit * twinkle + scan * (SCAN_FLAT + rim);
  };

  const organLight = (pillar: Pillar, seed: number, flow: number): number => {
    const flicker = 1 - ORGAN_FLICKER * triangle(now.seconds * ORGAN_FLICKER_SPEED + seed);
    const wave = flow === NO_FLOW ? 0 : crest(flow, now.seconds * FLOW_SPEED) * FLOW_GAIN;
    const breathing = now.alerting[pillar] ? now.pulse : 1;
    return now.strengths[pillar] * ORGAN_ALPHA * breathing * (flicker + wave);
  };

  /** Lumina particulelor neutre: pielea, nodurile, nervii și platforma. */
  const neutralLight = (group: number, at: number, seed: number, y: number, flow: number): number => {
    if (group === GROUP.dust) return skinLight(at, seed, y);
    if (group === GROUP.node) return NODE_BASE + skinLight(at, seed, y) * NODE_GAIN;
    if (group === GROUP.ground) return GROUND_ALPHA;
    const wave = flow === NO_FLOW ? 0 : crest(flow, now.seconds * NERVE_SPEED) * NERVE_WAVE;
    const scan = Math.max(0, 1 - Math.abs(y - now.scanY) / SCAN_WIDTH) * SCAN_GAIN;
    return NERVE_ALPHA * (1 + wave + scan);
  };

  /** Un punct al corpului (un organ, podeaua) pe ecran, fără mișcările particulelor. */
  const place = (point: Vec3): { readonly x: number; readonly y: number; readonly zoom: number } => {
    const turnedX = point[0] * now.cosYaw + point[Z_AXIS] * now.sinYaw;
    const turnedZ = point[Z_AXIS] * now.cosYaw - point[0] * now.sinYaw;
    const lifted = point[Y_AXIS] - PIVOT_HEIGHT;
    const zoom = (CAMERA_DISTANCE / (CAMERA_DISTANCE - (lifted * now.sinPitch + turnedZ * now.cosPitch))) * now.bodyHeight;
    return { x: now.axisX + turnedX * zoom, y: now.pivotY - (lifted * now.cosPitch - turnedZ * now.sinPitch) * zoom, zoom };
  };

  return (view: BodyView): void => {
    const ratio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
    resize(view, ratio);
    const { light, touched, image } = raster;
    const fogImage = fog.image;
    if (!image || !fogImage) return;
    const pixels = image.data;

    // șterge doar pixelii aprinși în cadrul trecut
    touched.subarray(0, raster.used).forEach((pixel) => {
      const at = pixel * RGB;
      light[at] = 0;
      light[at + GREEN] = 0;
      light[at + BLUE] = 0;
      pixels[pixel * RGBA + ALPHA] = 0;
    });
    raster.used = 0;
    fog.density.fill(0);

    const intro = view.moving ? view.time / INTRO_MS : INTRO_DONE;
    const settled = intro >= INTRO_SETTLED;
    const sinceScan = (view.time - SCAN_START_MS) % SCAN_EVERY_MS;
    const scanning = view.moving && view.time > SCAN_START_MS && sinceScan < SCAN_TRAVEL_MS;
    now.ratio = ratio;
    now.seconds = view.time / MS_PER_SECOND;
    now.cosYaw = Math.cos(view.yaw);
    now.sinYaw = Math.sin(view.yaw);
    now.cosPitch = Math.cos(view.pitch);
    now.sinPitch = Math.sin(view.pitch);
    now.axisX = view.axisX;
    now.pivotY = view.groundY - PIVOT_HEIGHT * view.bodyHeight;
    now.bodyHeight = view.bodyHeight;
    now.scanY = scanning ? (sinceScan / SCAN_TRAVEL_MS) * (1 + SCAN_MARGIN + SCAN_MARGIN) - SCAN_MARGIN : SCAN_AWAY;
    now.pulse = view.moving ? PULSE_BASE + PULSE_DEPTH * Math.sin((view.time / PULSE_PERIOD_MS) * FULL_TURN) : 1;
    now.swell = 1 + BEAT_SWELL * (view.moving ? heartbeat(view.time) : 0);
    now.strengths = view.strengths;
    now.alerting = view.alerting;
    now.tints = { behavioral: rgbOf(view.colors.behavioral), cardio: rgbOf(view.colors.cardio), immune: rgbOf(view.colors.immune), musculoskeletal: rgbOf(view.colors.musculoskeletal) };

    // 1. particulele: fiecare își adună lumina în tamponul de pixeli
    const density = ratio ** DENSITY_GAIN;
    seeds.forEach((seed, index) => {
      const at = index * AXES;
      const group = groups[index] ?? 0;
      const y = position[at + Y_AXIS] ?? 0;
      const appear = settled ? 1 : easeOut(clamp01((intro - y * INTRO_RISE - seed * INTRO_SCATTER) / INTRO_SPAN));
      if (appear <= 0) {
        alphas[index] = 0;
        return;
      }
      // inima se umflă în jurul centrului ei; restul particulelor stau pe loc
      const pumping = beats[index] ? now.swell : 1;
      const heartX = beats[index] ? HEART_CENTER[0] : 0;
      const heartY = beats[index] ? HEART_CENTER[Y_AXIS] : 0;
      const heartZ = beats[index] ? HEART_CENTER[Z_AXIS] : 0;
      const scatter = 1 - appear;
      const spread = 1 + scatter * INTRO_SPREAD;
      const x = (heartX + ((position[at] ?? 0) - heartX) * pumping) * spread;
      const z = (heartZ + ((position[at + Z_AXIS] ?? 0) - heartZ) * pumping) * spread;
      const raised = heartY + (y - heartY) * pumping - scatter * INTRO_DROP;
      const depth = settled
        ? project(x, raised, z, now.cosYaw, now.sinYaw, index)
        : project(x, raised, z, Math.cos(view.yaw + scatter * INTRO_SWIRL), Math.sin(view.yaw + scatter * INTRO_SWIRL), index);
      const pillar = PILLAR_BY_GROUP[group] ?? null;
      const flow = flows[index] ?? NO_FLOW;
      const lit = pillar ? organLight(pillar, seed, flow) : neutralLight(group, at, seed, y, flow);
      const alpha = Math.min(1, lit * (1 + depth * DEPTH_FADE) * appear);
      alphas[index] = alpha;
      if (group === GROUP.dust) thicken(screenX[index] ?? 0, screenY[index] ?? 0, appear);
      if (alpha < FAINT) return;
      // lumina unei particule crește cu suprafața ei; pe ecrane dese punctele ies mai fine, nu mai palide
      const size = SIZE_BY_GROUP[group] ?? DUST_SIZE;
      splat((screenX[index] ?? 0) * ratio, (screenY[index] ?? 0) * ratio, alpha * size * size * density, pillar ? now.tints[pillar] : cream);
    });

    // tamponul de lumină devine imagine: culoarea rămâne, luminozitatea e opacitatea; ce trece de 1 se albește
    touched.subarray(0, raster.used).forEach((pixel) => {
      const at = pixel * RGB;
      const out = pixel * RGBA;
      const red = light[at] ?? 0;
      const green = light[at + GREEN] ?? 0;
      const blue = light[at + BLUE] ?? 0;
      const peak = Math.max(red, green, blue, TINY);
      const glare = Math.max(0, peak - 1) * WHITEN;
      pixels[out] = (red / peak + glare) * BYTE;
      pixels[out + GREEN] = (green / peak + glare) * BYTE;
      pixels[out + BLUE] = (blue / peak + glare) * BYTE;
      pixels[out + ALPHA] = Math.min(1, peak) * BYTE;
    });
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.putImageData(image, 0, 0);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.globalCompositeOperation = "lighter";

    // 2. ceața: densitatea netezită cu vecinii, pictată mică și întinsă peste figură
    fog.density.forEach((_, cell) => {
      const around = FOG_BLUR.reduce<number>((sum, row) => sum + FOG_BLUR.reduce<number>((inRow, column) => inRow + (fog.density[cell + row * fog.cols + column] ?? 0), 0), 0);
      const out = cell * RGBA;
      fogImage.data[out] = cream[0] * BYTE;
      fogImage.data[out + GREEN] = cream[GREEN] * BYTE;
      fogImage.data[out + BLUE] = cream[BLUE] * BYTE;
      fogImage.data[out + ALPHA] = Math.min(1, (around / FOG_BLUR_CELLS) * FOG_GAIN) * BYTE;
    });
    fogBrush.putImageData(fogImage, 0, 0);
    context.globalAlpha = 1;
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    context.drawImage(fogCanvas, -FOG_CELL * HALF, -FOG_CELL * HALF, fog.cols * FOG_CELL, fog.rows * FOG_CELL);

    // 3. liniile dintre particule, adunate pe trepte de luminozitate ca să se tragă din câteva mișcări
    const linesIn = clamp01((intro - LINES_FROM) / LINES_SPAN);
    const strokes = new Map<string, Path2D>();
    linkFrom.forEach((from, link) => {
      const to = linkTo[link] ?? from;
      const pillar = PILLAR_BY_GROUP[groups[from] ?? 0] ?? null;
      const strength = Math.min(alphas[from] ?? 0, alphas[to] ?? 0) * (pillar ? ORGAN_LINE_GAIN : LINE_GAIN) * linesIn;
      if (strength < FAINT) return;
      const step = Math.min(LINE_BUCKETS, Math.ceil(strength * LINE_BUCKETS));
      const key = `${pillar ?? ""}:${step}`;
      const path = strokes.get(key) ?? new Path2D();
      strokes.set(key, path);
      path.moveTo(screenX[from] ?? 0, screenY[from] ?? 0);
      path.lineTo(screenX[to] ?? 0, screenY[to] ?? 0);
    });
    context.lineWidth = LINE_WIDTH;
    strokes.forEach((path, key) => {
      const [name = "", step = "1"] = key.split(":");
      const pillar = PILLAR_ORDER.find((candidate) => candidate === name) ?? null;
      context.strokeStyle = pillar ? view.colors[pillar] : CREAM;
      context.globalAlpha = Number(step) / LINE_BUCKETS;
      context.stroke(path);
    });

    // 4. lumina de pe podea și cea din jurul organelor
    const shown = clamp01((intro - GLOW_FROM) / GLOW_SPAN);
    const floor = place([0, 0, 0]);
    const floorWidth = FLOOR_GLOW_WIDTH * floor.zoom;
    const floorHeight = floorWidth * Math.abs(now.sinPitch) * FLOOR_FLATTEN;
    context.globalAlpha = FLOOR_GLOW_ALPHA * clamp01(intro / INTRO_SETTLED);
    context.drawImage(glow, floor.x - floorWidth, floor.y - floorHeight, floorWidth + floorWidth, floorHeight + floorHeight);
    if (scanning) {
      const ring = place([0, now.scanY, 0]);
      const ringWidth = SCAN_RING_RADIUS * ring.zoom;
      context.strokeStyle = CREAM;
      context.lineWidth = 1;
      // apare și dispare lin la capetele drumului
      context.globalAlpha = SCAN_RING_ALPHA * Math.sin((sinceScan / SCAN_TRAVEL_MS) * Math.PI);
      context.beginPath();
      context.ellipse(ring.x, ring.y, ringWidth, ringWidth * Math.abs(now.sinPitch), 0, 0, FULL_TURN);
      context.stroke();
    }
    cloud.halos.forEach((halo) => {
      const center = place(halo.c);
      const radius = halo.r * center.zoom * (halo.pillar === "cardio" ? now.swell : 1);
      context.fillStyle = view.colors[halo.pillar];
      const solid = String(context.fillStyle);
      const around = context.createRadialGradient(center.x, center.y, 0, center.x, center.y, radius);
      around.addColorStop(0, solid);
      around.addColorStop(1, `${solid}${TRANSPARENT_SUFFIX}`);
      context.fillStyle = around;
      context.globalAlpha = Math.min(1, view.strengths[halo.pillar] * HALO_ALPHA * (view.alerting[halo.pillar] ? now.pulse * HALO_ALERT_GAIN : 1) * shown);
      context.fillRect(center.x - radius, center.y - radius, radius + radius, radius + radius);
    });

    // 5. liniile spre etichete: un inel pe organ, apoi o linie frântă până la marginea etichetei
    context.globalCompositeOperation = "source-over";
    const { leaders } = view;
    if (!leaders) return;
    context.strokeStyle = CREAM;
    context.fillStyle = CREAM;
    context.lineWidth = 1;
    PILLAR_ORDER.forEach((pillar) => {
      const from = place(cloud.anchors[pillar]);
      const to = leaders[pillar];
      const elbowX = to.x + Math.sign(from.x - to.x) * LEADER_ELBOW;
      const reach = Math.hypot(elbowX - from.x, to.y - from.y) || 1;
      context.globalAlpha = (view.active === pillar ? LEADER_ACTIVE_ALPHA : LEADER_ALPHA) * shown;
      context.beginPath();
      context.arc(from.x, from.y, ANCHOR_RING, 0, FULL_TURN);
      context.moveTo(from.x + ((elbowX - from.x) / reach) * ANCHOR_RING, from.y + ((to.y - from.y) / reach) * ANCHOR_RING);
      context.lineTo(elbowX, to.y);
      context.lineTo(to.x, to.y);
      context.stroke();
      context.beginPath();
      context.arc(from.x, from.y, ANCHOR_DOT, 0, FULL_TURN);
      context.fill();
    });
  };
}
/* eslint-enable ts-patterns/no-param-reassign */
