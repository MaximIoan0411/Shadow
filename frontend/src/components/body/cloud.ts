/**
 * Corpul din particule: din anatomia descrisă în `anatomy.ts` face un nor de puncte 3D.
 *
 *  - pielea: mii de particule fine așezate exact pe suprafața corpului, plus noduri mai rare legate între ele
 *    într-o rețea (ochiurile care dau volumul);
 *  - înăuntru: coloana și nervii (neutri) și cele patru zone urmărite — creierul, inima, ganglionii, oasele;
 *  - sub tălpi: platforma din inele.
 *
 * Totul se calculează o singură dată, în browser, cu un generator cu sămânță: figura e aceeași la fiecare pornire.
 * Desenarea (rotația, lumina, culorile stărilor) e în `renderer.ts`.
 */
import { PILLAR_ORDER, type Pillar } from "@/lib/status";
import { BODY, GROUND, NERVES, ORGANS, ORGAN_LINK, SHELL, SPINE, TWIG, type BlobSpec, type ChainSpec, type ConeSpec, type EllipsoidSpec, type OrganSpec, type TubeSpec } from "./anatomy";
import {
  FULL_TURN,
  HALF,
  NO_NORMAL,
  add,
  alongCurve,
  coneField,
  curveTangent,
  distance,
  dot,
  ellipsoidField,
  fieldNormal,
  frameAround,
  mirrorX,
  normalize,
  randomDirection,
  sampleProfile,
  scale,
  seededRandom,
  smoothMin,
  sub,
  tiltZ,
  type Field,
  type Vec3,
} from "./math3";

/** Din ce face parte o particulă; după asta se alege cum se desenează. */
const GROUP_NAMES = ["dust", "node", "nerve", "ground", "behavioral", "cardio", "immune", "musculoskeletal"] as const;
export type GroupName = (typeof GROUP_NAMES)[number];
/** Numărul unui grup e poziția lui în listă. */
export type Group = number;
// `Object.fromEntries` întoarce chei `string`; cheile sunt exact numele din lista de mai sus
export const GROUP = Object.fromEntries(GROUP_NAMES.map((name, index) => [name, index])) as Readonly<Record<GroupName, Group>>;
export const GROUP_COUNT = GROUP_NAMES.length;

/** Grupul fiecărei zone urmărite. */
export const PILLAR_GROUP = {
  behavioral: GROUP.behavioral,
  cardio: GROUP.cardio,
  immune: GROUP.immune,
  musculoskeletal: GROUP.musculoskeletal,
} as const satisfies Record<Pillar, Group>;

/** Particulă fără undă care să treacă prin ea. */
export const NO_FLOW = -1;

interface Particle {
  readonly p: Vec3;
  readonly n: Vec3;
  readonly group: Group;
  /** Poziția de-a lungul drumului ei (plus un decalaj al drumului), pentru undele care trec; `NO_FLOW` dacă nu are. */
  readonly flow: number;
  readonly beats: boolean;
  readonly linked: boolean;
}

export interface Halo {
  readonly pillar: Pillar;
  readonly c: Vec3;
  readonly r: number;
}

export interface BodyCloud {
  readonly count: number;
  /** Câte trei valori pe particulă: x, y, z. */
  readonly position: Float32Array;
  /** Normala pielii în acel punct; zero pentru particulele din interior. */
  readonly normal: Float32Array;
  readonly group: Uint8Array;
  readonly flow: Float32Array;
  readonly beats: Uint8Array;
  /** Un număr la întâmplare pe particulă (0–1): sclipirea și ordinea de apariție. */
  readonly seed: Float32Array;
  /** Liniile dintre particule: perechi de indici. */
  readonly linkFrom: Uint16Array;
  readonly linkTo: Uint16Array;
  readonly halos: readonly Halo[];
  readonly anchors: Readonly<Record<Pillar, Vec3>>;
}

const SEED = 20261114;
/** Cât de departe de centrul unei celule mai poate fi suprafața ca celula să fie păstrată (jumătate de diagonală). */
const CELL_REACH = 0.9;
const KEY_OFFSET = 512;
const KEY_SPAN = 1024;
const PAIR_SPAN = 65536;
const PHASE_SPREAD = 7;
const TWIG_FLOW_STEP = 0.02;
/** Unghiul de aur, în radiani: pași care nu se aliniază niciodată. */
const GOLDEN_ANGLE = 2.39996;
const NEIGHBOR_STEPS = [-1, 0, 1] as const;

const particle = (p: Vec3, group: Group, extra: Partial<Particle> = {}): Particle => ({ p, n: NO_NORMAL, group, flow: NO_FLOW, beats: false, linked: false, ...extra });

// ---------------------------------------------------------------- suprafața corpului

interface Shapes {
  readonly ellipsoids: readonly EllipsoidSpec[];
  readonly cones: readonly ConeSpec[];
}

const toFields = (shapes: Shapes): readonly Field[] => [
  ...shapes.ellipsoids.map((shape) => ellipsoidField(shape.c, shape.r, shape.tilt)),
  ...shapes.cones.map((shape) => coneField(shape.a, shape.b, shape.ra, shape.rb)),
];

/** Distanța semnată până la piele: unirea lină a tuturor formelor, cu membrele oglindite. */
function bodyField(): Field {
  const center = toFields(BODY.center);
  const sides = toFields(BODY.sides);
  const union = (fields: readonly Field[], x: number, y: number, z: number, start: number): number =>
    fields.reduce((nearest, field) => smoothMin(nearest, field(x, y, z), BODY.blend), start);
  return (x, y, z) => union(sides, Math.abs(x), y, z, union(center, x, y, z, Number.POSITIVE_INFINITY));
}

/** Particule exact pe piele: se caută celulele prin care trece suprafața, apoi punctele din ele se aduc pe ea. */
function sampleSkin(field: Field, random: () => number): readonly Particle[] {
  const { min, max, cell, band, tries } = SHELL;
  const columns = Math.ceil((max[0] - min[0]) / cell);
  const rows = Math.ceil((max[1] - min[1]) / cell);
  const layers = Math.ceil((max[2] - min[2]) / cell);
  const centerOf = (index: number): Vec3 => [
    min[0] + ((index % columns) + HALF) * cell,
    min[1] + ((Math.floor(index / columns) % rows) + HALF) * cell,
    min[2] + (Math.floor(index / (columns * rows)) + HALF) * cell,
  ];
  const crossed = Array.from({ length: columns * rows * layers }, (_, index) => centerOf(index)).filter((c) => Math.abs(field(c[0], c[1], c[2])) < cell * CELL_REACH);
  return Array.from({ length: tries }, (): readonly Particle[] => {
    const c = crossed[Math.floor(random() * crossed.length)];
    if (!c) return [];
    const p: Vec3 = [c[0] + (random() - HALF) * cell, c[1] + (random() - HALF) * cell, c[2] + (random() - HALF) * cell];
    const value = field(p[0], p[1], p[2]);
    if (Math.abs(value) > band) return [];
    const n = fieldNormal(field, p, value);
    return [particle(sub(p, scale(n, value)), GROUP.dust, { n })];
  }).flat();
}

// ---------------------------------------------------------------- vecini

const cellIndex = (value: number, size: number): number => Math.floor(value / size) + KEY_OFFSET;
const keyOf = (ix: number, iy: number, iz: number): number => ix + iy * KEY_SPAN + iz * KEY_SPAN * KEY_SPAN;
const cellKey = (p: Vec3, size: number): number => keyOf(cellIndex(p[0], size), cellIndex(p[1], size), cellIndex(p[2], size));

/** Cheile celulei unui punct și ale celor 26 de celule vecine. */
const aroundKeys = (p: Vec3, size: number): readonly number[] =>
  NEIGHBOR_STEPS.flatMap((dx) =>
    NEIGHBOR_STEPS.flatMap((dy) => NEIGHBOR_STEPS.map((dz) => keyOf(cellIndex(p[0], size) + dx, cellIndex(p[1], size) + dy, cellIndex(p[2], size) + dz))),
  );

function addToGrid(grid: Map<number, number[]>, key: number, index: number): void {
  const bucket = grid.get(key);
  if (bucket) bucket.push(index);
  else grid.set(key, [index]);
}

/** Alege nodurile rețelei: particule de pe piele aflate la cel puțin `nodeSpacing` una de alta. */
function pickNodes(skin: readonly Particle[]): ReadonlySet<number> {
  const spacing = SHELL.nodeSpacing;
  const grid = new Map<number, number[]>();
  const chosen = new Set<number>();
  skin.forEach((candidate, index) => {
    const crowded = aroundKeys(candidate.p, spacing).some((key) => (grid.get(key) ?? []).some((other) => distance(skin[other]?.p ?? candidate.p, candidate.p) < spacing));
    if (crowded) return;
    chosen.add(index);
    addToGrid(grid, cellKey(candidate.p, spacing), index);
  });
  return chosen;
}

/** Leagă fiecare particulă din `indices` de cei mai apropiați vecini ai ei; fiecare pereche apare o singură dată. */
function linkNearest(particles: readonly Particle[], indices: readonly number[], reach: number, most: number, sameSide: boolean): readonly (readonly [number, number])[] {
  const grid = new Map<number, number[]>();
  indices.forEach((index) => {
    const self = particles[index];
    if (self) addToGrid(grid, cellKey(self.p, reach), index);
  });
  const seen = new Set<number>();
  return indices.flatMap((index) => {
    const self = particles[index];
    if (!self) return [];
    return aroundKeys(self.p, reach)
      .flatMap((key) => grid.get(key) ?? [])
      .flatMap((other) => {
        const neighbor = particles[other];
        if (!neighbor || other === index) return [];
        const far = distance(neighbor.p, self.p);
        // pe piele nu se leagă puncte de pe fețe opuse (brațul de trunchi, un picior de celălalt)
        return far < reach && (!sameSide || dot(neighbor.n, self.n) > 0) ? [{ other, far }] : [];
      })
      .sort((a, b) => a.far - b.far)
      .slice(0, most)
      .flatMap(({ other }): readonly (readonly [number, number])[] => {
        const low = Math.min(index, other);
        const high = Math.max(index, other);
        const id = low * PAIR_SPAN + high;
        if (seen.has(id)) return [];
        seen.add(id);
        return [[low, high]];
      });
  });
}

// ---------------------------------------------------------------- interiorul

const mirrored = <TItem>(mirror: boolean | undefined, build: (flip: boolean) => readonly TItem[]): readonly TItem[] => (mirror ? [...build(false), ...build(true)] : build(false));

/** Un organ rotunjit: particule într-un elipsoid, mai dese spre suprafață cu cât `hollow` e mai mare. */
function blobParticles(spec: BlobSpec, group: Group, random: () => number): readonly Particle[] {
  return mirrored(spec.mirror, (flip) =>
    Array.from({ length: spec.count }, (): Particle => {
      const direction = randomDirection(random);
      const depth = spec.hollow + (1 - spec.hollow) * Math.cbrt(random());
      const local: Vec3 = [direction[0] * spec.r[0] * depth, direction[1] * spec.r[1] * depth, direction[2] * spec.r[2] * depth];
      const placed = add(spec.c, tiltZ(local, spec.tilt ?? 0));
      return particle(flip ? mirrorX(placed) : placed, group, { beats: Boolean(spec.beats), linked: Boolean(spec.linked) });
    }),
  );
}

/** Un os sau un vas: particule pe suprafața unui tub cu raza variabilă, în jurul unui drum. */
function tubeParticles(spec: TubeSpec, group: Group, random: () => number): readonly Particle[] {
  return mirrored(spec.mirror, (flip) => {
    const path = flip ? spec.path.map(mirrorX) : spec.path;
    const phase = random() * PHASE_SPREAD;
    // particulele urcă în spirală pe tub, la pași egali: osul iese curat, nu ca un nor
    return Array.from({ length: spec.count }, (_, index): Particle => {
      const t = (index + HALF) / spec.count;
      const [side, up] = frameAround(curveTangent(path, t));
      const angle = index * GOLDEN_ANGLE;
      const radius = sampleProfile(spec.radius, t);
      const around = add(scale(side, Math.cos(angle) * radius), scale(up, Math.sin(angle) * radius));
      return particle(add(alongCurve(path, t), around), group, { flow: spec.flows ? phase + t : NO_FLOW });
    });
  });
}

interface Walk {
  readonly p: Vec3;
  readonly heading: Vec3;
  readonly alive: boolean;
  readonly trail: readonly Particle[];
}

/** O rămurică de nerv: câțiva pași care șerpuiesc, cad ușor în jos și se opresc când ajung la piele. */
function twigParticles(path: readonly Vec3[], phase: number, group: Group, random: () => number, skin: Field): readonly Particle[] {
  const t = TWIG.from + random() * (1 - TWIG.from);
  const droop: Vec3 = [0, -TWIG.droop, 0];
  const start: Walk = { p: alongCurve(path, t), heading: normalize(add(randomDirection(random), droop)), alive: true, trail: [] };
  return Array.from({ length: TWIG.steps }, (_, step) => step + 1).reduce<Walk>((walk, step) => {
    if (!walk.alive) return walk;
    const heading = normalize(add(walk.heading, add(scale(randomDirection(random), TWIG.wander), scale(droop, TWIG.wander))));
    const p = add(walk.p, scale(heading, TWIG.stride));
    if (skin(p[0], p[1], p[2]) > TWIG.skin) return { ...walk, alive: false };
    return { p, heading, alive: true, trail: [...walk.trail, particle(p, group, { flow: phase + t + step * TWIG_FLOW_STEP })] };
  }, start).trail;
}

/** Un nerv sau un vas limfatic: un șir de particule de-a lungul unui drum, cu rămurelele lui. */
function chainParticles(spec: ChainSpec, group: Group, random: () => number, skin: Field): readonly Particle[] {
  return mirrored(spec.mirror, (flip) => {
    const path = flip ? spec.path.map(mirrorX) : spec.path;
    const phase = random() * PHASE_SPREAD;
    const main = Array.from({ length: spec.count }, (_, index): Particle => {
      const t = (index + random()) / spec.count;
      return particle(add(alongCurve(path, t), scale(randomDirection(random), spec.jitter * random())), group, { flow: phase + t });
    });
    const twigs = Array.from({ length: spec.twigs ?? 0 }, () => twigParticles(path, phase, group, random, skin)).flat();
    return [...main, ...twigs];
  });
}

/** Coloana: vertebre din inele de particule, cu apofizele lor, și sacrul. */
function spineParticles(random: () => number): readonly Particle[] {
  const { ring, height, squash, spinous, wing } = SPINE;
  const vertebrae = Array.from({ length: SPINE.vertebrae }, (_, index) => {
    const t = index / (SPINE.vertebrae - 1);
    const center = alongCurve(SPINE.path, t);
    const radius = sampleProfile(SPINE.radius, t);
    const body = Array.from({ length: ring + ring }, (__, k): Vec3 => {
      const angle = (k / ring) * FULL_TURN;
      const level = k < ring ? -HALF : HALF;
      return [center[0] + Math.cos(angle) * radius, center[1] + level * height, center[2] + Math.sin(angle) * radius * squash];
    });
    const back = Array.from({ length: spinous.count }, (__, k): Vec3 => [center[0], center[1] - (k + 1) * spinous.drop, center[2] - radius * squash - (k + 1) * spinous.back]);
    const wings = [-1, 1].flatMap((sign) => Array.from({ length: wing.count }, (__, k): Vec3 => [center[0] + sign * (radius + (k + 1) * wing.out), center[1], center[2] - radius * wing.back]));
    return [...body, ...back, ...wings].map((p) => particle(p, GROUP.nerve));
  }).flat();
  const sacrum = tubeParticles({ path: SPINE.sacrum.path, radius: SPINE.sacrum.radius, count: SPINE.sacrum.count }, GROUP.nerve, random);
  return [...vertebrae, ...sacrum];
}

function organParticles(organ: OrganSpec, group: Group, random: () => number, skin: Field): readonly Particle[] {
  return [
    ...organ.blobs.flatMap((spec) => blobParticles(spec, group, random)),
    ...organ.tubes.flatMap((spec) => tubeParticles(spec, group, random)),
    ...organ.chains.flatMap((spec) => chainParticles(spec, group, random, skin)),
  ];
}

const groundParticles = (): readonly Particle[] =>
  GROUND.flatMap(({ radius, count }) =>
    Array.from({ length: count }, (_, index): Particle => {
      const angle = (index / count) * FULL_TURN;
      return particle([Math.cos(angle) * radius, 0, Math.sin(angle) * radius], GROUP.ground);
    }),
  );

// ---------------------------------------------------------------- norul întreg

function buildBodyCloud(): BodyCloud {
  const random = seededRandom(SEED);
  const skinField = bodyField();
  const skin = sampleSkin(skinField, random);
  const nodes = pickNodes(skin);
  const dust = skin.filter((_, index) => !nodes.has(index)).slice(0, SHELL.dust);
  const nodeParticles = skin.filter((_, index) => nodes.has(index)).map((node): Particle => ({ ...node, group: GROUP.node }));
  const nerves = [...spineParticles(random), ...NERVES.flatMap((spec) => chainParticles(spec, GROUP.nerve, random, skinField))];
  const organs = PILLAR_ORDER.flatMap((pillar) => organParticles(ORGANS[pillar], PILLAR_GROUP[pillar], random, skinField));
  const particles = [...dust, ...nodeParticles, ...nerves, ...groundParticles(), ...organs];

  const indicesOf = (keep: (candidate: Particle) => boolean): readonly number[] => particles.flatMap((candidate, index) => (keep(candidate) ? [index] : []));
  const links = [
    ...linkNearest(particles, indicesOf((candidate) => candidate.group === GROUP.node), SHELL.linkReach, SHELL.linkMax, true),
    ...PILLAR_ORDER.flatMap((pillar) => linkNearest(particles, indicesOf((candidate) => candidate.linked && candidate.group === PILLAR_GROUP[pillar]), ORGAN_LINK.reach, ORGAN_LINK.most, false)),
  ];
  const halos = PILLAR_ORDER.flatMap((pillar) =>
    (ORGANS[pillar] as OrganSpec).halos.flatMap((halo): readonly Halo[] => mirrored(halo.mirror, (flip) => [{ pillar, c: flip ? mirrorX(halo.c) : halo.c, r: halo.r }])),
  );

  return {
    count: particles.length,
    position: Float32Array.from(particles.flatMap((item) => item.p)),
    normal: Float32Array.from(particles.flatMap((item) => item.n)),
    group: Uint8Array.from(particles, (item) => item.group),
    flow: Float32Array.from(particles, (item) => item.flow),
    beats: Uint8Array.from(particles, (item) => Number(item.beats)),
    seed: Float32Array.from(particles, () => random()),
    linkFrom: Uint16Array.from(links, (link) => link[0]),
    linkTo: Uint16Array.from(links, (link) => link[1]),
    halos,
    anchors: { behavioral: ORGANS.behavioral.anchor, cardio: ORGANS.cardio.anchor, immune: ORGANS.immune.anchor, musculoskeletal: ORGANS.musculoskeletal.anchor },
  };
}

const cache: { cloud: BodyCloud | null } = { cloud: null };

/** Norul corpului; se calculează la prima cerere și apoi se refolosește. */
export function getBodyCloud(): BodyCloud {
  cache.cloud ??= buildBodyCloud();
  return cache.cloud;
}
