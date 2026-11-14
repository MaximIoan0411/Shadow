/* eslint-disable ts-patterns/no-magic-numbers -- tabel de proporții anatomice: fiecare număr e o poziție sau o rază pe corp */
/**
 * Anatomia corpului din particule, ca date. Unități: înălțimea corpului = 1; `x` spre dreapta privitorului
 * (stânga corpului), `y` în sus de la tălpi, `z` spre privitor.
 *
 * Suprafața corpului e o unire lină de elipsoizi și conuri rotunjite (proporții de adult, brațele ușor depărtate,
 * palmele în față). Înăuntru: creierul, inima cu aorta, ganglionii limfatici cu vasele lor și oasele picioarelor
 * (cele patru zone urmărite, colorate după stare), plus coloana și nervii, care rămân neutri.
 * Nimic de aici nu depinde de date: starea fiecărei zone se aplică la desenare.
 */
import type { Pillar } from "@/lib/status";
import type { Vec3 } from "./math3";

export interface EllipsoidSpec {
  readonly c: Vec3;
  readonly r: Vec3;
  /** Înclinarea în jurul axei Z, în radiani. */
  readonly tilt?: number;
}

export interface ConeSpec {
  readonly a: Vec3;
  readonly b: Vec3;
  readonly ra: number;
  readonly rb: number;
}

interface Shapes {
  readonly ellipsoids: readonly EllipsoidSpec[];
  readonly cones: readonly ConeSpec[];
}

/** Suprafața corpului. `sides` e desenat pe partea dreaptă a privitorului și oglindit. */
export const BODY = {
  /** Lățimea racordului dintre forme. */
  blend: 0.02,
  center: {
    ellipsoids: [
      { c: [0, 0.94, -0.004], r: [0.045, 0.056, 0.056] }, // craniul
      { c: [0, 0.905, 0.014], r: [0.035, 0.046, 0.042] }, // fața și maxilarul
      { c: [0, 0.914, 0.054], r: [0.008, 0.015, 0.01] }, // nasul
      { c: [0, 0.74, -0.004], r: [0.09, 0.098, 0.06] }, // cutia toracică
      { c: [0, 0.618, 0.004], r: [0.073, 0.088, 0.05] }, // abdomenul
      { c: [0, 0.515, -0.004], r: [0.088, 0.06, 0.056] }, // bazinul
    ],
    cones: [{ a: [0, 0.835, -0.008], b: [0, 0.888, -0.002], ra: 0.031, rb: 0.027 }], // gâtul
  },
  sides: {
    ellipsoids: [
      { c: [0.047, 0.926, -0.006], r: [0.006, 0.015, 0.009] }, // urechea
      { c: [0.116, 0.8, -0.004], r: [0.039, 0.044, 0.04] }, // umărul
      { c: [0.045, 0.757, 0.034], r: [0.045, 0.034, 0.026] }, // pectoralul
      { c: [0.072, 0.7, -0.022], r: [0.03, 0.07, 0.034] }, // dorsalul
      { c: [0.188, 0.45, 0.02], r: [0.021, 0.036, 0.0105] }, // palma
      { c: [0.194, 0.406, 0.025], r: [0.018, 0.03, 0.008] }, // degetele
      { c: [0.045, 0.502, -0.034], r: [0.046, 0.05, 0.038] }, // fesierul
      { c: [0.056, 0.284, 0.01], r: [0.033, 0.036, 0.034] }, // genunchiul
      { c: [0.059, 0.2, -0.018], r: [0.029, 0.062, 0.03] }, // gamba
      { c: [0.058, 0.017, 0.032], r: [0.025, 0.017, 0.06] }, // laba piciorului
      { c: [0.054, 0.022, -0.018], r: [0.021, 0.022, 0.022] }, // călcâiul
    ],
    cones: [
      { a: [0.02, 0.852, -0.012], b: [0.098, 0.82, -0.008], ra: 0.027, rb: 0.03 }, // trapezul
      { a: [0.121, 0.79, -0.004], b: [0.151, 0.636, -0.008], ra: 0.033, rb: 0.026 }, // brațul
      { a: [0.151, 0.636, -0.008], b: [0.18, 0.492, 0.012], ra: 0.028, rb: 0.017 }, // antebrațul
      { a: [0.202, 0.458, 0.024], b: [0.224, 0.426, 0.03], ra: 0.008, rb: 0.006 }, // degetul mare
      { a: [0.05, 0.49, 0], b: [0.056, 0.29, 0.004], ra: 0.056, rb: 0.036 }, // coapsa
      { a: [0.056, 0.27, 0.002], b: [0.054, 0.05, -0.006], ra: 0.033, rb: 0.019 }, // gamba (tibia)
    ],
  },
} as const satisfies { readonly blend: number; readonly center: Shapes; readonly sides: Shapes };

/** Cutia în care se caută suprafața și cum se eșantionează. */
export const SHELL = {
  min: [-0.25, -0.01, -0.1],
  max: [0.25, 1.01, 0.11],
  /** Latura celulei grilei de căutare. */
  cell: 0.02,
  /** Cât de aproape de suprafață trebuie să cadă un punct ca să fie păstrat (apoi e adus exact pe ea). */
  band: 0.003,
  tries: 70000,
  /** Câte particule fine are pielea. */
  dust: 7000,
  /** Distanța minimă dintre nodurile rețelei de pe piele. */
  nodeSpacing: 0.0235,
  /** Până la ce distanță și cu câți vecini se leagă un nod. */
  linkReach: 0.045,
  linkMax: 5,
} as const;

// ---------------------------------------------------------------- organele (zonele colorate după stare)

export interface BlobSpec {
  readonly c: Vec3;
  readonly r: Vec3;
  readonly tilt?: number;
  readonly count: number;
  /** 0 = particule în tot volumul, 1 = doar pe suprafață. */
  readonly hollow: number;
  readonly mirror?: boolean;
  /** Particulele se leagă între ele cu linii (rețeaua creierului, a inimii). */
  readonly linked?: boolean;
  /** Se mișcă odată cu bătaia inimii. */
  readonly beats?: boolean;
}

export interface TubeSpec {
  readonly path: readonly Vec3[];
  /** Raza de-a lungul drumului, de la un capăt la celălalt. */
  readonly radius: readonly number[];
  readonly count: number;
  readonly mirror?: boolean;
  /** Pe tub trece o undă (sângele prin aortă). */
  readonly flows?: boolean;
}

export interface ChainSpec {
  readonly path: readonly Vec3[];
  readonly count: number;
  /** Cât se abat particulele de la drum. */
  readonly jitter: number;
  readonly mirror?: boolean;
  /** Câte rămurele subțiri pornesc din drum. */
  readonly twigs?: number;
}

export interface HaloSpec {
  readonly c: Vec3;
  /** Raza luminii din jur, în unități de corp. */
  readonly r: number;
  readonly mirror?: boolean;
}

export interface OrganSpec {
  readonly blobs: readonly BlobSpec[];
  readonly tubes: readonly TubeSpec[];
  readonly chains: readonly ChainSpec[];
  readonly halos: readonly HaloSpec[];
  /** Punctul de pe corp din care pleacă linia spre eticheta zonei. */
  readonly anchor: Vec3;
}

export const HEART_CENTER: Vec3 = [0.02, 0.738, 0.02];

export const ORGANS = {
  // creierul: două emisfere, cerebelul și trunchiul cerebral
  behavioral: {
    blobs: [
      { c: [0.0178, 0.948, -0.006], r: [0.0178, 0.03, 0.043], count: 210, hollow: 0.8, mirror: true, linked: true },
      { c: [0, 0.918, -0.034], r: [0.021, 0.011, 0.015], count: 56, hollow: 0.6, linked: true },
    ],
    tubes: [{ path: [[0, 0.93, -0.014], [0, 0.912, -0.016], [0, 0.893, -0.014]], radius: [0.008, 0.006, 0.005], count: 44 }],
    chains: [],
    halos: [{ c: [0, 0.945, -0.006], r: 0.075 }],
    anchor: [0, 0.95, 0],
  },
  // inima, cu arcul aortei, aorta descendentă și carotidele
  cardio: {
    blobs: [
      { c: HEART_CENTER, r: [0.026, 0.034, 0.023], tilt: 0.5, count: 300, hollow: 0.72, linked: true, beats: true },
      { c: [0.006, 0.756, 0.024], r: [0.016, 0.016, 0.014], count: 70, hollow: 0.7, linked: true, beats: true },
    ],
    tubes: [
      {
        path: [[0.012, 0.764, 0.018], [0.016, 0.79, 0.014], [0.004, 0.806, 0.002], [-0.008, 0.796, -0.012], [-0.006, 0.74, -0.02], [-0.004, 0.66, -0.016], [-0.002, 0.58, -0.012], [0, 0.553, -0.01]],
        radius: [0.0085, 0.008, 0.0075, 0.007, 0.0065, 0.006, 0.0055, 0.005],
        count: 330,
        flows: true,
      },
      { path: [[0.008, 0.804, 0.004], [0.016, 0.84, 0.002], [0.019, 0.885, 0.004]], radius: [0.004, 0.0035, 0.003], count: 60, mirror: true, flows: true },
      { path: [[0, 0.553, -0.01], [0.03, 0.52, -0.004], [0.05, 0.492, 0.008]], radius: [0.0045, 0.004, 0.0035], count: 50, mirror: true, flows: true },
    ],
    chains: [],
    halos: [{ c: HEART_CENTER, r: 0.07 }],
    anchor: [0.026, 0.74, 0.02],
  },
  // sistemul imunitar: ganglionii de la gât, axile, splină, abdomen și inghinali, legați prin vasele limfatice
  immune: {
    blobs: [
      { c: [0.025, 0.872, 0.012], r: [0.0085, 0.0105, 0.0085], count: 46, hollow: 0.3, mirror: true },
      { c: [0.09, 0.773, 0.004], r: [0.013, 0.015, 0.013], count: 78, hollow: 0.3, mirror: true },
      { c: [0.06, 0.668, -0.012], r: [0.017, 0.026, 0.015], tilt: -0.35, count: 130, hollow: 0.45 },
      { c: [-0.02, 0.606, 0.022], r: [0.011, 0.012, 0.01], count: 54, hollow: 0.3 },
      { c: [0.022, 0.588, 0.022], r: [0.011, 0.012, 0.01], count: 54, hollow: 0.3 },
      { c: [0.034, 0.474, 0.036], r: [0.011, 0.0125, 0.01], count: 60, hollow: 0.3, mirror: true },
    ],
    tubes: [],
    chains: [
      // canalul toracic: din abdomen până la baza gâtului, în stânga corpului
      { path: [[0, 0.56, 0.006], [0.004, 0.63, -0.008], [0.004, 0.72, -0.02], [0.006, 0.8, -0.016], [0.03, 0.842, -0.002]], count: 110, jitter: 0.0016 },
      { path: [[0.034, 0.474, 0.036], [0.03, 0.53, 0.026], [0.022, 0.588, 0.022], [0, 0.56, 0.006]], count: 44, jitter: 0.0016 },
      { path: [[-0.034, 0.474, 0.036], [-0.032, 0.535, 0.026], [-0.02, 0.606, 0.022], [0, 0.56, 0.006]], count: 48, jitter: 0.0016 },
      { path: [[0.06, 0.668, -0.012], [0.03, 0.65, -0.012], [0.004, 0.63, -0.008]], count: 28, jitter: 0.0016 },
      { path: [[0.09, 0.773, 0.004], [0.07, 0.815, 0], [0.03, 0.842, -0.002]], count: 34, jitter: 0.0016, mirror: true },
      { path: [[0.025, 0.872, 0.012], [0.03, 0.855, 0.004], [0.03, 0.842, -0.002]], count: 14, jitter: 0.0012, mirror: true },
    ],
    halos: [
      { c: [0.025, 0.872, 0.012], r: 0.024, mirror: true },
      { c: [0.09, 0.773, 0.004], r: 0.034, mirror: true },
      { c: [0.06, 0.668, -0.012], r: 0.042 },
      { c: [0, 0.597, 0.022], r: 0.04 },
      { c: [0.034, 0.474, 0.036], r: 0.032, mirror: true },
    ],
    anchor: [-0.09, 0.773, 0.004],
  },
  // oasele picioarelor: femurul, rotula, tibia, fibula și laba piciorului
  musculoskeletal: {
    blobs: [
      { c: [0.04, 0.507, 0], r: [0.0125, 0.0125, 0.0125], count: 44, hollow: 0.9, mirror: true },
      { c: [0.057, 0.288, 0.03], r: [0.0085, 0.0105, 0.005], count: 30, hollow: 0.8, mirror: true },
    ],
    tubes: [
      {
        path: [[0.04, 0.507, 0], [0.061, 0.494, 0], [0.064, 0.47, 0.002], [0.06, 0.39, 0.006], [0.057, 0.31, 0.006], [0.057, 0.292, 0.006]],
        radius: [0.008, 0.0075, 0.0105, 0.0075, 0.008, 0.016],
        count: 250,
        mirror: true,
      },
      { path: [[0.056, 0.274, 0.004], [0.056, 0.25, 0.003], [0.055, 0.16, 0], [0.054, 0.07, -0.004], [0.054, 0.048, -0.004]], radius: [0.0155, 0.0095, 0.0065, 0.0065, 0.0095], count: 220, mirror: true },
      { path: [[0.073, 0.262, -0.008], [0.072, 0.16, -0.01], [0.068, 0.046, -0.01]], radius: [0.0045, 0.003, 0.0045], count: 70, mirror: true },
      { path: [[0.054, 0.034, -0.014], [0.057, 0.026, 0.02], [0.059, 0.014, 0.052], [0.06, 0.009, 0.078]], radius: [0.011, 0.01, 0.0095, 0.006], count: 80, mirror: true },
    ],
    chains: [],
    halos: [{ c: [0.057, 0.288, 0.012], r: 0.046, mirror: true }],
    anchor: [0.06, 0.39, 0.006],
  },
} as const satisfies Record<Pillar, OrganSpec>;

// ---------------------------------------------------------------- coloana și nervii (neutri)

/** Coloana, de la prima vertebră cervicală până la sacru, cu curburile ei. */
export const SPINE = {
  path: [[0, 0.888, -0.016], [0, 0.862, -0.01], [0, 0.832, -0.018], [0, 0.77, -0.036], [0, 0.7, -0.036], [0, 0.62, -0.02], [0, 0.56, -0.016], [0, 0.527, -0.026]],
  vertebrae: 24,
  /** Raza corpului vertebral, de la gât la bazin. */
  radius: [0.0075, 0.0085, 0.011, 0.0135],
  /** Câte particule are inelul unei vertebre și cât de înaltă e. */
  ring: 11,
  height: 0.0062,
  /** Vertebra e mai îngustă în adâncime decât în lățime. */
  squash: 0.82,
  /** Apofiza spinoasă (spre spate) și cele transverse (în lateral): câte puncte și cât de departe. */
  spinous: { count: 3, back: 0.0042, drop: 0.0022 },
  wing: { count: 2, out: 0.0048, back: 0.6 },
  /** Sacrul: se îngustează în jos. */
  sacrum: { path: [[0, 0.522, -0.03], [0, 0.498, -0.042], [0, 0.474, -0.04]], radius: [0.014, 0.009, 0.003], count: 90 },
} as const;

/** Un nerv intercostal: pleacă din coloană și înconjoară cutia toracică până în față. */
function rib(y: number): readonly Vec3[] {
  const fit = 0.84;
  const level = Math.sqrt(Math.max(0, 1 - ((y - 0.74) / 0.098) ** 2));
  const half = 0.09 * level * fit;
  const depth = 0.06 * level * fit;
  return [
    [0.012, y, -depth * 0.74],
    [half * 0.62, y - 0.004, -depth * 0.86],
    [half, y - 0.014, -depth * 0.16],
    [half * 0.84, y - 0.026, depth * 0.58],
    [half * 0.46, y - 0.034, depth * 0.9],
  ];
}

const RIB_LEVELS = [0.818, 0.802, 0.786, 0.769, 0.752, 0.735, 0.718, 0.701, 0.684, 0.667] as const;

export const NERVES: readonly ChainSpec[] = [
  // măduva spinării
  { path: [[0, 0.893, -0.014], [0, 0.862, -0.012], [0, 0.832, -0.02], [0, 0.77, -0.038], [0, 0.7, -0.038], [0, 0.62, -0.022], [0, 0.575, -0.018]], count: 240, jitter: 0.0022 },
  // plexul brahial și nervul brațului, până în palmă
  { path: [[0.006, 0.862, -0.012], [0.05, 0.838, -0.01], [0.108, 0.806, -0.006], [0.134, 0.72, -0.006], [0.151, 0.636, -0.006], [0.166, 0.56, 0.004], [0.181, 0.49, 0.014], [0.188, 0.455, 0.02]], count: 150, jitter: 0.0026, mirror: true, twigs: 16 },
  // degetele
  { path: [[0.188, 0.455, 0.02], [0.178, 0.42, 0.024], [0.176, 0.39, 0.026]], count: 16, jitter: 0.0012, mirror: true },
  { path: [[0.188, 0.455, 0.02], [0.188, 0.416, 0.025], [0.188, 0.382, 0.027]], count: 18, jitter: 0.0012, mirror: true },
  { path: [[0.188, 0.455, 0.02], [0.198, 0.418, 0.025], [0.2, 0.385, 0.027]], count: 18, jitter: 0.0012, mirror: true },
  { path: [[0.188, 0.455, 0.02], [0.207, 0.424, 0.025], [0.211, 0.396, 0.026]], count: 16, jitter: 0.0012, mirror: true },
  { path: [[0.19, 0.46, 0.02], [0.208, 0.448, 0.026], [0.223, 0.427, 0.03]], count: 14, jitter: 0.0012, mirror: true },
  // nervul sciatic, până în talpă
  { path: [[0.004, 0.575, -0.018], [0.03, 0.535, -0.024], [0.05, 0.495, -0.022], [0.056, 0.4, -0.012], [0.057, 0.3, -0.012], [0.058, 0.2, -0.016], [0.055, 0.08, -0.008], [0.056, 0.03, 0.006], [0.059, 0.014, 0.06]], count: 190, jitter: 0.0028, mirror: true, twigs: 20 },
  // nervul femural, în fața coapsei
  { path: [[0.004, 0.6, -0.016], [0.036, 0.54, 0.008], [0.054, 0.47, 0.026], [0.056, 0.38, 0.024], [0.055, 0.31, 0.022]], count: 80, jitter: 0.0026, mirror: true, twigs: 8 },
  // nervii intercostali
  ...RIB_LEVELS.map((y): ChainSpec => ({ path: rib(y), count: 44, jitter: 0.0016, mirror: true })),
];

/** Rămurelele nervilor: pași scurți, care cad ușor în jos și se opresc la piele. */
export const TWIG = { steps: 9, stride: 0.0042, wander: 0.5, droop: 0.35, skin: -0.004, from: 0.12 } as const;

/** Cât de departe se leagă între ele particulele unui organ „în rețea” (creierul, inima) și cu câți vecini. */
export const ORGAN_LINK = { reach: 0.0125, most: 3 } as const;

/** Platforma de sub tălpi: inele de puncte. */
export const GROUND = [
  { radius: 0.15, count: 64 },
  { radius: 0.215, count: 92 },
  { radius: 0.29, count: 124 },
] as const;
