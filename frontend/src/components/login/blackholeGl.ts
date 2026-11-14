/**
 * Motorul de desenare al găurii negre: WebGL2 simplu, fără biblioteci.
 *
 * Un cadru are patru etape: scena (shaderul care curbează lumina) se desenează într-o imagine cu valori peste 1
 * (HDR), la o rezoluție care se poate micșora pe plăci video lente; din ea se face strălucirea, pe o piramidă de
 * imagini din ce în ce mai mici; apoi totul se adună pe pânză, cu tonurile de film.
 */
import { COMPOSITE, DOWN, SCENE, UP, VERTEX } from "./blackholeShaders";

export interface BlackHoleFrame {
  /** Secunde de la apariție: rotește discul și mișcă granulația. */
  readonly time: number;
  readonly camera: readonly [number, number, number];
  /** Orientarea camerei: nouă numere, pe coloane (dreapta, sus, înainte). */
  readonly view: Float32Array;
  readonly focal: number;
  /** Unde stă gaura pe pânză, 0–1 (y în sus). */
  readonly center: readonly [number, number];
  /** Apariția din negru, 0–1. */
  readonly fade: number;
}

export interface BlackHoleRenderer {
  /** Mărimea pânzei în pixeli de ecran și cât din ea e rezoluția scenei (0–1). */
  readonly resize: (width: number, height: number, quality: number) => void;
  readonly render: (frame: BlackHoleFrame) => void;
  readonly dispose: () => void;
}

interface Target {
  readonly texture: WebGLTexture;
  readonly buffer: WebGLFramebuffer;
  readonly width: number;
  readonly height: number;
}

interface Targets {
  readonly scene: Target;
  /** Treptele strălucirii, de la jumătate de scenă în jos. */
  readonly down: readonly Target[];
  /** Aceleași trepte, adunate de jos în sus; prima e strălucirea finală. */
  readonly up: readonly Target[];
}

const BLOOM_LEVELS = 6;
const BLOOM_THRESHOLD = 0.9;
/** Strălucirea se întinde mai mult pe orizontală, ca printr-un obiectiv anamorfic. */
const BLOOM_SPREAD_X = 1.9;
const BLOOM_SPREAD_Y = 1;
const TRIANGLE_VERTICES = 3;
const HALVE = 0.5;

function compile(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
  console.error("SHADOW: black hole shader failed to compile", gl.getShaderInfoLog(shader));
  gl.deleteShader(shader);
  return null;
}

function link(gl: WebGL2RenderingContext, fragmentSource: string): WebGLProgram | null {
  const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  if (!vertex || !fragment || !program) return null;
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (gl.getProgramParameter(program, gl.LINK_STATUS)) return program;
  console.error("SHADOW: black hole program failed to link", gl.getProgramInfoLog(program));
  gl.deleteProgram(program);
  return null;
}

/** O imagine în care se poate desena; cu `hdr` ține valori peste 1 (lumina discului nu se taie înainte de strălucire). */
function createTarget(gl: WebGL2RenderingContext, width: number, height: number, hdr: boolean): Target | null {
  const texture = gl.createTexture();
  const buffer = gl.createFramebuffer();
  if (!texture || !buffer) return null;
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texImage2D(gl.TEXTURE_2D, 0, hdr ? gl.RGBA16F : gl.RGBA8, width, height, 0, gl.RGBA, hdr ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.bindFramebuffer(gl.FRAMEBUFFER, buffer);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
  return { texture, buffer, width, height };
}

const isTarget = (target: Target | null): target is Target => target !== null;

function createTargets(gl: WebGL2RenderingContext, width: number, height: number, hdr: boolean): Targets | null {
  const scene = createTarget(gl, width, height, hdr);
  const half = (size: number, level: number): number => Math.max(1, Math.floor(size * HALVE ** (level + 1)));
  const level = (index: number): Target | null => createTarget(gl, half(width, index), half(height, index), hdr);
  const down = Array.from({ length: BLOOM_LEVELS }, (_, index) => level(index)).filter(isTarget);
  const up = Array.from({ length: BLOOM_LEVELS - 1 }, (_, index) => level(index)).filter(isTarget);
  if (!scene || down.length !== BLOOM_LEVELS || up.length !== BLOOM_LEVELS - 1) return null;
  return { scene, down, up };
}

function deleteTargets(gl: WebGL2RenderingContext, targets: Targets | null): void {
  if (!targets) return;
  [targets.scene, ...targets.down, ...targets.up].forEach((target) => {
    gl.deleteTexture(target.texture);
    gl.deleteFramebuffer(target.buffer);
  });
}

/* eslint-disable ts-patterns/no-param-reassign -- mărimea pânzei se setează prin atribuire (`canvas.width = …`) */
/** Pregătește desenarea pe `canvas`. Întoarce `null` dacă browserul nu are WebGL2 sau shaderele nu se compilează. */
export function createBlackHoleRenderer(canvas: HTMLCanvasElement): BlackHoleRenderer | null {
  const gl = canvas.getContext("webgl2", { alpha: false, antialias: false, depth: false, stencil: false, powerPreference: "high-performance" });
  if (!gl) return null;
  const hdr = Boolean(gl.getExtension("EXT_color_buffer_float") ?? gl.getExtension("EXT_color_buffer_half_float"));
  const scene = link(gl, SCENE);
  const down = link(gl, DOWN);
  const up = link(gl, UP);
  const composite = link(gl, COMPOSITE);
  if (!scene || !down || !up || !composite) return null;
  // locul fiecărei variabile de shader se caută o singură dată
  const places = new Map<WebGLProgram, Map<string, WebGLUniformLocation | null>>();
  const at = (program: WebGLProgram, name: string): WebGLUniformLocation | null => {
    const known = places.get(program) ?? new Map<string, WebGLUniformLocation | null>();
    places.set(program, known);
    if (!known.has(name)) known.set(name, gl.getUniformLocation(program, name));
    return known.get(name) ?? null;
  };
  const state: { targets: Targets | null } = { targets: null };

  /** Desenează triunghiul de ecran cu un program, într-o imagine sau (cu `null`) direct pe pânză. */
  const pass = (program: WebGLProgram, target: Target | null, setUniforms: () => void): void => {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.buffer : null);
    gl.viewport(0, 0, target ? target.width : canvas.width, target ? target.height : canvas.height);
    gl.useProgram(program);
    setUniforms();
    gl.drawArrays(gl.TRIANGLES, 0, TRIANGLE_VERTICES);
  };

  const sample = (program: WebGLProgram, name: string, unit: number, source: Target): void => {
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, source.texture);
    gl.uniform1i(at(program, name), unit);
  };

  return {
    resize: (width, height, quality) => {
      canvas.width = width;
      canvas.height = height;
      deleteTargets(gl, state.targets);
      state.targets = createTargets(gl, Math.max(1, Math.round(width * quality)), Math.max(1, Math.round(height * quality)), hdr);
    },

    render: (frame) => {
      const { targets } = state;
      if (!targets || gl.isContextLost()) return;

      pass(scene, targets.scene, () => {
        gl.uniform2f(at(scene, "uResolution"), targets.scene.width, targets.scene.height);
        gl.uniform2f(at(scene, "uCenter"), frame.center[0], frame.center[1]);
        gl.uniform1f(at(scene, "uTime"), frame.time);
        gl.uniform3f(at(scene, "uCamera"), frame.camera[0], frame.camera[1], frame.camera[2]);
        gl.uniformMatrix3fv(at(scene, "uView"), false, frame.view);
        gl.uniform1f(at(scene, "uFocal"), frame.focal);
      });

      // strălucirea: în jos pe piramidă (prima treaptă păstrează doar ce e luminos)…
      targets.down.forEach((target, index) => {
        const source = targets.down[index - 1] ?? targets.scene;
        pass(down, target, () => {
          sample(down, "uSource", 0, source);
          gl.uniform2f(at(down, "uTexel"), 1 / source.width, 1 / source.height);
          gl.uniform1f(at(down, "uThreshold"), index ? 0 : BLOOM_THRESHOLD);
        });
      });
      // …și înapoi în sus, adunând fiecare treaptă peste cea de deasupra ei
      [...targets.up].reverse().forEach((target, reversed) => {
        const index = targets.up.length - 1 - reversed;
        const small = targets.up[index + 1] ?? targets.down[index + 1];
        const large = targets.down[index];
        if (!small || !large) return;
        pass(up, target, () => {
          sample(up, "uSmall", 0, small);
          sample(up, "uLarge", 1, large);
          gl.uniform2f(at(up, "uTexel"), 1 / small.width, 1 / small.height);
          gl.uniform2f(at(up, "uSpread"), BLOOM_SPREAD_X, BLOOM_SPREAD_Y);
        });
      });

      const bloom = targets.up[0];
      if (!bloom) return;
      pass(composite, null, () => {
        sample(composite, "uScene", 0, targets.scene);
        sample(composite, "uBloom", 1, bloom);
        gl.uniform2f(at(composite, "uCenter"), frame.center[0], frame.center[1]);
        gl.uniform1f(at(composite, "uTime"), frame.time);
        gl.uniform1f(at(composite, "uFade"), frame.fade);
      });
    },

    dispose: () => {
      deleteTargets(gl, state.targets);
      state.targets = null;
      [scene, down, up, composite].forEach((program) => gl.deleteProgram(program));
    },
  };
}
/* eslint-enable ts-patterns/no-param-reassign */
