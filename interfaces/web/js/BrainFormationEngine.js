// Procedurally generates the Empire Brain's target geometry: two
// hemispheres with a real central fissure and organic gyrification, a
// narrowing brainstem, ambient floating particles, and the short-range +
// major-pathway connections between them. Nothing here is a 2D silhouette
// projected flat -- every point is a real 3D position, and the brain reads
// as anatomical from any camera angle.
//
// Deliberately NOT using a general-purpose noise library (simplex/perlin)
// -- a small sum of sine waves at incommensurate frequencies is cheap,
// dependency-free, always well-behaved (no edge cases to debug blind),
// and organic-looking enough for gyrus-style surface perturbation.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";

// Division color palette. Real feedback from the first render: one
// attractor per division with an inverse-SQUARE falloff let the nearest
// attractor dominate its whole local region almost exclusively (gold
// reading as a solid, separate "bottom zone" instead of interweaving) --
// exactly the "compartmentalized" look that was flagged. Fixed two ways:
// each division now has 2-3 satellite points scattered at different
// places in the volume (so no single color owns one contiguous region),
// and the falloff is linear with a much larger epsilon (softer, wider
// reach per point) instead of inverse-square.
export const DIVISION_COLORS = {
  rii: { hex: 0x36e0ff, pos: [new THREE.Vector3(-0.32, 0.3, 0.32), new THREE.Vector3(0.25, -0.15, 0.35)] },
  learning: { hex: 0xc060ff, pos: [new THREE.Vector3(0.34, 0.35, -0.28), new THREE.Vector3(-0.2, -0.3, -0.15)] },
  fixera: { hex: 0xff9b30, pos: [new THREE.Vector3(-0.38, -0.15, -0.22), new THREE.Vector3(0.15, 0.4, -0.1)] },
  forex: { hex: 0x33e08a, pos: [new THREE.Vector3(0.4, -0.12, 0.26), new THREE.Vector3(-0.3, 0.2, 0.15)] },
  systems: { hex: 0x4ea3ff, pos: [new THREE.Vector3(0.0, 0.45, 0.08), new THREE.Vector3(0.3, -0.35, -0.2)] },
  audit: { hex: 0x8b5cf6, pos: [new THREE.Vector3(0.02, 0.12, -0.42), new THREE.Vector3(-0.15, -0.5, 0.1)] },
  orchestrator: {
    hex: 0xffc24b,
    // still weighted toward the brainstem/core (it's the routing layer),
    // but with satellites reaching up into both hemispheres so gold
    // threads through the whole structure, not just the trunk
    pos: [new THREE.Vector3(0.0, -0.55, 0.0), new THREE.Vector3(-0.15, 0.15, 0.05), new THREE.Vector3(0.18, 0.1, -0.05)],
  },
};

// Two octaves for broad gyrus bumps, a third, higher-frequency one for
// finer wrinkle detail -- amplitude raised from the first pass (0.22 max
// combined) since the folds read as barely-there density noise rather
// than visible ridges next to the reference.
function gyrus(d) {
  return (
    0.16 * Math.sin(d.x * 8 + 1.7) * Math.cos(d.y * 10 + 0.4) +
    0.11 * Math.sin(d.y * 13 + 2.3) * Math.sin(d.z * 9 + 1.1) +
    0.09 * Math.cos(d.x * 6) * Math.sin(d.z * 14 + 0.9) +
    0.06 * Math.sin(d.x * 21 + d.z * 17 + 3.1) * Math.cos(d.y * 19 + 1.4)
  );
}

function fibonacciDir(i, n) {
  const phi = Math.acos(1 - (2 * (i + 0.5)) / n); // 0 (top pole) .. PI (bottom pole)
  const golden = Math.PI * (1 + Math.sqrt(5));
  const theta = golden * i;
  return new THREE.Vector3(Math.sin(phi) * Math.cos(theta), Math.cos(phi), Math.sin(phi) * Math.sin(theta));
}

const _c1 = new THREE.Color();
const _c2 = new THREE.Color();
function blendedColor(worldPos) {
  let r = 0,
    g = 0,
    b = 0,
    wSum = 0;
  for (const key in DIVISION_COLORS) {
    const div = DIVISION_COLORS[key];
    _c1.setHex(div.hex);
    for (const p of div.pos) {
      const dist = worldPos.distanceTo(p);
      const w = 1 / (dist + 0.22); // linear falloff, wide epsilon -- soft, far-reaching blend
      r += _c1.r * w;
      g += _c1.g * w;
      b += _c1.b * w;
      wSum += w;
    }
  }
  _c2.setRGB(r / wSum, g / wSum, b / wSum);
  return _c2.clone();
}

const GAP = 0.28; // hemisphere center offset from x=0
const SEMI = { x: 0.56, y: 0.58, z: 0.5 }; // taller (y raised) -- a real screenshot showed the cortex reading flat/funnel-like, not domed
const GROOVE = 0.12; // half-width of the enforced central fissure
const GROOVE_MIN_Y = -0.25; // fissure enforced over a much taller band -- was only near the very top, barely visible

export class BrainFormationEngine {
  constructor({ hemisphereCount = 7000, brainstemCount = 1400, ambientCount = 500 } = {}) {
    this.hemisphereCount = hemisphereCount;
    this.brainstemCount = brainstemCount;
    this.ambientCount = ambientCount;
    this.pedestalOrbitCount = 220;
    this.total = hemisphereCount + brainstemCount + ambientCount + this.pedestalOrbitCount;
  }

  /** Returns typed arrays ready for NeuralParticleSystem, plus the raw
   * point list (with real 3D positions) for NeuralNetwork/EnergyPaths to
   * build connections from. */
  generate() {
    const n = this.total;
    const starts = new Float32Array(n * 3);
    const targets = new Float32Array(n * 3);
    const colors = new Float32Array(n * 3);
    const startTimes = new Float32Array(n);
    const durations = new Float32Array(n);
    const sizes = new Float32Array(n);
    const phases = new Float32Array(n);
    const orbitRadius = new Float32Array(n); // 0 = not an orbit particle
    const orbitY = new Float32Array(n);
    const orbitSpeed = new Float32Array(n);

    const points = []; // { target: Vector3, isBrainstem, isAmbient }
    let idx = 0;

    const SCATTER_RADIUS = 2.4;
    const randomScatterPoint = () => {
      const v = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5);
      v.normalize().multiplyScalar(SCATTER_RADIUS * (0.4 + Math.random() * 0.6));
      return v;
    };

    // ---- hemispheres ----
    const perHemisphere = Math.floor(this.hemisphereCount / 2);
    for (const side of [-1, 1]) {
      for (let i = 0; i < perHemisphere; i++) {
        const d = fibonacciDir(i, perHemisphere);
        const g = 1 + gyrus(d);
        // Real shape bug found from a live screenshot: tapering the whole
        // bottom HALF (d.y<0) down to 0.5 width made the hemisphere and the
        // brainstem below it blend into one continuous, monotonic taper --
        // reading as a funnel/cone, not "round cortex sitting above a
        // distinct narrow stem". Fixed by keeping the hemisphere round and
        // full through most of its lower half, and only pinching sharply
        // in the last stretch near its true bottom -- a real "neck" the
        // brainstem's own separate, much-smaller top radius then continues
        // from, instead of a smooth continuous cone.
        let bottomTaper = 1.0;
        if (d.y < -0.55) bottomTaper = THREE.MathUtils.lerp(1.0, 0.34, THREE.MathUtils.smoothstep(-d.y, 0.55, 1.0));

        const local = new THREE.Vector3(d.x * SEMI.x * g * bottomTaper, d.y * SEMI.y * g, d.z * SEMI.z * g * bottomTaper);
        const world = new THREE.Vector3(local.x + side * GAP, local.y + 0.05, local.z);

        // enforce the central fissure: push points out of the groove band
        // in the upper region only, matching how a real longitudinal
        // fissure doesn't reach the brain's base.
        if (world.y > GROOVE_MIN_Y && Math.abs(world.x) < GROOVE) {
          const sign = world.x >= 0 ? 1 : -1;
          world.x = sign * GROOVE * (0.6 + Math.random() * 0.5);
        }

        const target = world;
        const start = randomScatterPoint();
        const color = blendedColor(target);

        starts[idx * 3] = start.x;
        starts[idx * 3 + 1] = start.y;
        starts[idx * 3 + 2] = start.z;
        targets[idx * 3] = target.x;
        targets[idx * 3 + 1] = target.y;
        targets[idx * 3 + 2] = target.z;
        colors[idx * 3] = color.r;
        colors[idx * 3 + 1] = color.g;
        colors[idx * 3 + 2] = color.b;

        // formation order: near the brainstem connection (low world y)
        // arrives earlier than the outer skull (high world y) -- "clusters
        // form, then hemispheres, then the full structure" per the brief.
        const heightFrac = THREE.MathUtils.clamp((world.y + 0.5) / 1.1, 0, 1);
        startTimes[idx] = 0.3 + 0.65 * heightFrac + Math.random() * 0.05;
        durations[idx] = 0.14 + Math.random() * 0.12;
        // world-space diameter, converted to real screen pixels by
        // uSizeAttenuation in the shader -- see ParticleShader.js's comment
        sizes[idx] = 0.006 + Math.random() * 0.007;
        phases[idx] = Math.random();

        points.push({ target, isBrainstem: false, isAmbient: false, index: idx });
        idx++;
      }
    }

    // ---- brainstem: real feedback was that this read as a straight funnel
    // separate from the brain rather than an organic extension of it.
    // Fixed three ways: stemTop now roughly matches the hemisphere neck's
    // own pinched width (continuity, not a sudden jump to a thin cone),
    // the taper curve (pow 1.8, not 1.3) stays wide longer near the top
    // and narrows late rather than shrinking evenly the whole way down,
    // and the cross-section gets angular+height-dependent noise so it's
    // not a perfect circle at any height -- an irregular, organic column.
    const stemTop = -0.5,
      stemBottom = -0.95;
    const stemSteps = 46;
    let stemIdx = 0;
    while (stemIdx < this.brainstemCount) {
      const t = Math.random(); // 0 = top (wide), 1 = bottom (narrow)
      const y = THREE.MathUtils.lerp(stemTop, stemBottom, t);
      const baseRadius = THREE.MathUtils.lerp(0.22, 0.05, Math.pow(t, 1.8));
      const ang = Math.random() * Math.PI * 2;
      const irregular = 1 + 0.2 * Math.sin(ang * 5 + t * 7) + 0.12 * Math.cos(ang * 8 - t * 4);
      const radius = baseRadius * irregular;
      const rr = radius * Math.sqrt(Math.random());
      const sway = 0.035 * Math.sin(t * Math.PI * 3.1 + ang) * (1 - t * 0.6);
      const target = new THREE.Vector3(Math.cos(ang) * rr + sway, y, Math.sin(ang) * rr);
      const start = randomScatterPoint();
      const color = blendedColor(target);

      starts[idx * 3] = start.x;
      starts[idx * 3 + 1] = start.y;
      starts[idx * 3 + 2] = start.z;
      targets[idx * 3] = target.x;
      targets[idx * 3 + 1] = target.y;
      targets[idx * 3 + 2] = target.z;
      colors[idx * 3] = color.r;
      colors[idx * 3 + 1] = color.g;
      colors[idx * 3 + 2] = color.b;

      startTimes[idx] = 0.05 * t + Math.random() * 0.15;
      durations[idx] = 0.12 + Math.random() * 0.1;
      sizes[idx] = 0.005 + Math.random() * 0.006;
      phases[idx] = Math.random();

      points.push({ target, isBrainstem: true, isAmbient: false, index: idx });
      idx++;
      stemIdx++;
    }
    void stemSteps; // kept for documentation of intended density; loop is count-driven

    // ---- ambient floating particles surrounding the structure (Layer 5) ----
    for (let i = 0; i < this.ambientCount; i++) {
      // ambient particles wander loosely near the brain rather than
      // forming a hard structure -- their formation target IS a resting
      // wander-center, reusing the shader's generic lerp(start,target).
      // x range found live to be too wide: at the group's own +0.55 world
      // offset, a symmetric +-1.1 let ambient particles wander left past
      // the brain entirely and into the left card column's screen space
      // (confirmed via gl.readPixels showing lit pixels as far left as
      // x=106px on an 828px canvas, well inside the ~276px-wide card
      // zone). Biased right and narrowed so ambient particles stay around
      // the brain instead of drifting into the UI.
      const wanderCenter = new THREE.Vector3(
        THREE.MathUtils.lerp(-0.35, 0.95, Math.random()),
        (Math.random() - 0.5) * 1.6 - 0.1,
        (Math.random() - 0.5) * 2.0
      );
      const start = randomScatterPoint();
      const color = blendedColor(wanderCenter);

      starts[idx * 3] = start.x;
      starts[idx * 3 + 1] = start.y;
      starts[idx * 3 + 2] = start.z;
      targets[idx * 3] = wanderCenter.x;
      targets[idx * 3 + 1] = wanderCenter.y;
      targets[idx * 3 + 2] = wanderCenter.z;
      colors[idx * 3] = color.r;
      colors[idx * 3 + 1] = color.g;
      colors[idx * 3 + 2] = color.b;

      startTimes[idx] = Math.random() * 0.6;
      durations[idx] = 0.3 + Math.random() * 0.3;
      sizes[idx] = 0.004 + Math.random() * 0.005;
      phases[idx] = Math.random();

      points.push({ target: wanderCenter, isBrainstem: false, isAmbient: true, index: idx });
      idx++;
    }

    // ---- pedestal orbit particles ----
    for (let i = 0; i < this.pedestalOrbitCount; i++) {
      const radius = 0.35 + Math.random() * 0.32;
      const y = stemBottom - 0.03 + Math.random() * 0.02;
      const start = randomScatterPoint();
      const color = blendedColor(new THREE.Vector3(0, stemBottom, 0));

      starts[idx * 3] = start.x;
      starts[idx * 3 + 1] = start.y;
      starts[idx * 3 + 2] = start.z;
      targets[idx * 3] = 0;
      targets[idx * 3 + 1] = y;
      targets[idx * 3 + 2] = 0;
      colors[idx * 3] = color.r;
      colors[idx * 3 + 1] = color.g;
      colors[idx * 3 + 2] = color.b;

      startTimes[idx] = 0.5 + Math.random() * 0.3;
      durations[idx] = 0.15 + Math.random() * 0.1;
      sizes[idx] = 0.005 + Math.random() * 0.004;
      phases[idx] = Math.random();
      orbitRadius[idx] = radius;
      orbitY[idx] = y;
      orbitSpeed[idx] = 0.15 + Math.random() * 0.2;

      idx++;
    }

    return {
      count: n,
      starts,
      targets,
      colors,
      startTimes,
      durations,
      sizes,
      phases,
      orbitRadius,
      orbitY,
      orbitSpeed,
      points, // for NeuralNetwork / EnergyPaths connection-building (excludes orbit/ambient by convention -- callers filter as needed)
      stemTop,
      stemBottom,
    };
  }
}
