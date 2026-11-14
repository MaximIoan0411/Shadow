/**
 * Shaderele găurii negre de pe ecranul de intrare (GLSL ES 3.00, pentru WebGL2).
 *
 * `SCENE` urmărește fiecare rază de lumină înapoi, de la cameră, prin spațiul curbat din jurul unei găuri negre
 * Schwarzschild (raza orizontului = 1): raza se îndoaie după ecuația geodezicei, iar de fiecare dată când
 * străpunge planul discului de acreție adună lumina lui. Așa apar singure arcul de deasupra umbrei (partea din
 * spate a discului, văzută pe deasupra), cel de dedesubt și inelul de fotoni. Discul are efect Doppler (partea
 * care vine spre privitor e mai luminoasă), iar stelele din fundal se curbează în jurul găurii.
 *
 * Restul sunt pași de imagine: `DOWN` și `UP` fac strălucirea (bloom) pe o piramidă de imagini tot mai mici, iar
 * `COMPOSITE` le adună, aplică tonurile de film (ACES), vinieta, o ușoară aberație cromatică și granulație.
 */

/** Un triunghi care acoperă tot ecranul, fără tampoane de vârfuri. */
export const VERTEX = `#version 300 es
out vec2 vUv;
void main() {
  vec2 corner = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  vUv = corner;
  gl_Position = vec4(corner * 2.0 - 1.0, 0.0, 1.0);
}`;

export const SCENE = `#version 300 es
precision highp float;

uniform vec2 uResolution;
uniform vec2 uCenter;      // unde stă gaura pe ecran, 0..1
uniform float uTime;
uniform vec3 uCamera;      // poziția camerei; raza orizontului = 1
uniform mat3 uView;        // coloane: dreapta, sus, înainte
uniform float uFocal;
out vec4 outColor;

const float PI = 3.14159265;
const float R_IN = 2.6;    // marginea dinăuntru a discului
const float R_OUT = 11.5;
const int STEPS = 240;

float hash21(vec2 p) {
  p = fract(p * vec2(234.34, 435.345));
  p += dot(p, p + 34.23);
  return fract(p.x * p.y);
}

float hash31(vec3 p) {
  p = fract(p * vec3(0.1031, 0.1030, 0.0973));
  p += dot(p, p.yzx + 33.33);
  return fract((p.x + p.y) * p.z);
}

// zgomot neted, periodic pe y (unghiul din jurul discului se închide fără cusătură)
float pnoise(vec2 p, float period) {
  vec2 cell = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float y0 = mod(cell.y, period);
  float y1 = mod(cell.y + 1.0, period);
  float a = hash21(vec2(cell.x, y0));
  float b = hash21(vec2(cell.x + 1.0, y0));
  float c = hash21(vec2(cell.x, y1));
  float d = hash21(vec2(cell.x + 1.0, y1));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p, float period) {
  float sum = 0.0;
  float gain = 0.5;
  for (int octave = 0; octave < 5; octave++) {
    sum += gain * pnoise(p, period);
    p *= 2.0;
    period *= 2.0;
    gain *= 0.5;
  }
  return sum;
}

// de la jar la alb fierbinte, în culorile logo-ului
vec3 heat(float t) {
  vec3 color = mix(vec3(0.30, 0.035, 0.008), vec3(0.95, 0.30, 0.055), smoothstep(0.0, 0.38, t));
  color = mix(color, vec3(1.0, 0.66, 0.30), smoothstep(0.30, 0.68, t));
  color = mix(color, vec3(1.0, 0.93, 0.80), smoothstep(0.62, 1.05, t));
  return color;
}

// dârele discului la o rază și un unghi; gazul se rotește mai repede spre centru
float streaks(float r, float angle, float seed) {
  float turn = angle / (2.0 * PI);
  float broad = fbm(vec2(r * 1.7 + seed, turn * 3.0), 3.0);
  float fine = fbm(vec2(r * 7.5 + seed * 3.1, turn * 6.0), 6.0);
  float rings = fbm(vec2(r * 21.0 + seed * 5.3, turn * 4.0), 4.0);
  return broad * 0.5 + fine * 0.3 + rings * 0.35;
}

// lumina discului în punctul în care raza îi străpunge planul (rgb înmulțit cu opacitatea, opacitatea)
vec4 disk(vec3 hit, vec3 travel) {
  float r = length(hit.xz);
  if (r < R_IN || r > R_OUT) return vec4(0.0);
  float angle = atan(hit.z, hit.x);
  float speed = 2.4 * pow(r, -1.5);

  // Rotația diferită pe fiecare rază ar răsuci dârele la nesfârșit; două straturi decalate, care se reiau pe
  // rând și se topesc unul în altul, țin mișcarea continuă fără să se strice desenul.
  const float LOOP = 26.0;
  float phaseA = fract(uTime / LOOP);
  float phaseB = fract(uTime / LOOP + 0.5);
  float weightA = 1.0 - abs(2.0 * phaseA - 1.0);
  float weightB = 1.0 - weightA;
  float a = streaks(r, angle - speed * phaseA * LOOP, 0.0);
  float b = streaks(r, angle - speed * phaseB * LOOP + 2.4, 41.0);
  float texture_ = (a * weightA + b * weightB - 0.55) / sqrt(weightA * weightA + weightB * weightB) + 0.55;
  texture_ = clamp(texture_, 0.0, 1.4);

  float inner = smoothstep(R_IN, R_IN + 0.7, r);
  float outer = 1.0 - smoothstep(R_OUT * 0.42, R_OUT, r);
  float profile = pow(R_IN / r, 1.9) * inner * outer;

  // efectul Doppler și înroșirea gravitațională
  vec3 orbit = normalize(vec3(-hit.z, 0.0, hit.x));
  float beta = min(0.62, sqrt(0.5 / r));
  float gamma = inversesqrt(1.0 - beta * beta);
  float doppler = 1.0 / (gamma * (1.0 - beta * dot(orbit, -travel)));
  float shift = doppler * sqrt(max(0.0, 1.0 - 1.0 / r));

  float temperature = pow(R_IN / r, 0.75) * (0.42 + 0.72 * shift) * (0.62 + 0.55 * texture_);
  float contrast = 0.12 + 1.9 * texture_ * texture_;
  vec3 light = heat(temperature) * profile * pow(shift, 2.1) * contrast * 3.9;

  // privit pe muchie, discul e mai dens
  float grazing = 1.0 / max(abs(travel.y), 0.22);
  float alpha = clamp(profile * 2.6 * (0.35 + 0.75 * texture_) * (0.55 + 0.25 * grazing), 0.0, 1.0);
  return vec4(light * alpha, alpha);
}

vec3 starfield(vec3 dir) {
  vec3 color = vec3(0.0);
  for (int layer = 0; layer < 3; layer++) {
    float scale = 34.0 * pow(2.15, float(layer));
    vec3 q = dir * scale + float(layer) * 19.7;
    vec3 cell = floor(q);
    float pick = hash31(cell);
    float rare = layer == 0 ? 0.972 : 0.950;
    if (pick > rare) {
      vec3 center = vec3(hash31(cell + 3.1), hash31(cell + 7.3), hash31(cell + 11.9)) * 0.6 + 0.2;
      float away = length(fract(q) - center);
      float bright = pow((pick - rare) / (1.0 - rare), 3.0);
      float core = smoothstep(0.10, 0.0, away);
      vec3 tint = mix(vec3(1.0, 0.80, 0.60), vec3(0.78, 0.86, 1.0), hash31(cell + 5.5));
      color += tint * core * core * (0.22 + 2.6 * bright);
    }
  }
  // o fâșie slabă de praf, înclinată față de disc: se vede cum o îndoaie gaura
  vec3 tilted = vec3(dir.x, dir.y * 0.82 + dir.z * 0.57, dir.z * 0.82 - dir.y * 0.57);
  float around = atan(tilted.z, tilted.x) / (2.0 * PI);
  float band = exp(-pow(tilted.y * 3.4, 2.0));
  float dust = fbm(vec2(tilted.y * 5.0 + 9.0, around * 10.0), 10.0);
  color += vec3(0.050, 0.030, 0.020) * band * dust * dust * dust * 1.5;
  color += vec3(0.004, 0.005, 0.009) * fbm(vec2(dir.y * 3.0, around * 6.0 + 3.0), 6.0);
  return color;
}

void main() {
  vec2 uv = (gl_FragCoord.xy - uCenter * uResolution) / uResolution.y;
  vec3 dir = normalize(uView * vec3(uv, uFocal));
  vec3 p = uCamera;
  vec3 v = dir;
  vec3 swing = cross(p, v);
  float h2 = dot(swing, swing);

  vec3 color = vec3(0.0);
  float through = 1.0;
  bool swallowed = false;

  for (int i = 0; i < STEPS; i++) {
    float r2 = dot(p, p);
    float r = sqrt(r2);
    if (r < 1.0) { swallowed = true; break; }
    if (r > 46.0 && dot(p, v) > 0.0) break;

    float dt = clamp(0.105 * (r - 0.7), 0.018, 1.6);
    // ecuația geodezicei pentru lumină în jurul unei găuri negre care nu se rotește
    vec3 pull = -1.5 * h2 * p / (r2 * r2 * r);
    vec3 nextV = v + pull * dt;
    vec3 nextP = p + nextV * dt;

    // ceața fierbinte din jurul discului: îi dă grosime
    float flat_ = length(p.xz);
    float haze = exp(-pow(p.y / (0.05 * flat_ + 0.04), 2.0)) * pow(R_IN / max(flat_, R_IN), 2.6);
    haze *= smoothstep(R_IN - 0.3, R_IN + 0.5, flat_) * (1.0 - smoothstep(R_OUT * 0.5, R_OUT, flat_));
    color += through * vec3(1.0, 0.42, 0.13) * haze * dt * 0.016;

    if (p.y * nextP.y < 0.0) {
      vec3 hit = mix(p, nextP, p.y / (p.y - nextP.y));
      vec4 glow = disk(hit, normalize(nextV));
      color += through * glow.rgb;
      through *= 1.0 - glow.a;
      if (through < 0.015) break;
    }
    p = nextP;
    v = nextV;
  }

  if (!swallowed) color += through * starfield(normalize(v));
  outColor = vec4(color, 1.0);
}`;

/** Micșorează imaginea la jumătate; la primul pas păstrează doar ce e destul de luminos ca să strălucească. */
export const DOWN = `#version 300 es
precision highp float;
uniform sampler2D uSource;
uniform vec2 uTexel;
uniform float uThreshold;   // 0 = fără prag
in vec2 vUv;
out vec4 outColor;

vec3 bright(vec3 c) {
  if (uThreshold <= 0.0) return c;
  float peak = max(c.r, max(c.g, c.b));
  return c * smoothstep(uThreshold, uThreshold * 2.4, peak);
}

void main() {
  vec3 sum = bright(texture(uSource, vUv).rgb) * 4.0;
  sum += bright(texture(uSource, vUv + uTexel * vec2(-1.0, -1.0)).rgb);
  sum += bright(texture(uSource, vUv + uTexel * vec2(1.0, -1.0)).rgb);
  sum += bright(texture(uSource, vUv + uTexel * vec2(-1.0, 1.0)).rgb);
  sum += bright(texture(uSource, vUv + uTexel * vec2(1.0, 1.0)).rgb);
  outColor = vec4(sum / 8.0, 1.0);
}`;

/** Mărește treapta mică, o netezește și o adună peste treapta de deasupra; întinsă pe orizontală, ca un obiectiv de film. */
export const UP = `#version 300 es
precision highp float;
uniform sampler2D uSmall;
uniform sampler2D uLarge;
uniform vec2 uTexel;        // un pixel din treapta mică
uniform vec2 uSpread;
in vec2 vUv;
out vec4 outColor;

void main() {
  vec2 d = uTexel * uSpread;
  vec3 sum = texture(uSmall, vUv).rgb * 4.0;
  sum += texture(uSmall, vUv + vec2(d.x, 0.0)).rgb * 2.0;
  sum += texture(uSmall, vUv - vec2(d.x, 0.0)).rgb * 2.0;
  sum += texture(uSmall, vUv + vec2(0.0, d.y)).rgb * 2.0;
  sum += texture(uSmall, vUv - vec2(0.0, d.y)).rgb * 2.0;
  sum += texture(uSmall, vUv + d).rgb;
  sum += texture(uSmall, vUv - d).rgb;
  sum += texture(uSmall, vUv + vec2(d.x, -d.y)).rgb;
  sum += texture(uSmall, vUv + vec2(-d.x, d.y)).rgb;
  // fiecare treaptă mai largă contează puțin mai puțin, ca strălucirea să nu devină ceață
  outColor = vec4(sum / 16.0 * 0.78 + texture(uLarge, vUv).rgb, 1.0);
}`;

export const COMPOSITE = `#version 300 es
precision highp float;
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform vec2 uCenter;
uniform float uTime;
uniform float uFade;        // 0..1: apariția din negru
in vec2 vUv;
out vec4 outColor;

float hash21(vec2 p) {
  p = fract(p * vec2(234.34, 435.345));
  p += dot(p, p + 34.23);
  return fract(p.x * p.y);
}

// curba de tonuri ACES (aproximarea lui Narkowicz)
vec3 film(vec3 x) {
  return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}

void main() {
  vec2 off = vUv - uCenter;
  // aberație cromatică, tot mai mare spre margini
  vec2 fringe = off * dot(off, off) * 0.012;
  vec3 color = vec3(texture(uScene, vUv + fringe).r, texture(uScene, vUv).g, texture(uScene, vUv - fringe).b);
  color += texture(uBloom, vUv).rgb * 0.26;
  color = film(color * 1.05 * uFade);
  color = pow(color, vec3(1.0 / 2.2));
  color *= 1.0 - 0.5 * smoothstep(0.38, 1.05, length(off * vec2(1.0, 1.15)));
  color += (hash21(gl_FragCoord.xy + fract(uTime) * 91.7) - 0.5) * (2.2 / 255.0);
  outColor = vec4(color, 1.0);
}`;
