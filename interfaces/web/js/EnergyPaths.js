// Layer 3 (major pathways) + Layer 4 (traveling pulses). Picks a handful
// of real, far-apart structural particles and threads a tube through
// nearby real points between them, so these read as thicker "trunk lines"
// of the same neural mesh rather than arbitrary decoration -- then a
// small number of bright points travel along each path continuously,
// reusing the same connection shader as NeuralNetwork (a path is just a
// thicker, always-visible connection, not a different kind of object).

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";
import { lineVertexShader, lineFragmentShader } from "./NeuralShader.js";

// Reduced from 11 -- feedback was that major pathways should read as
// sparse and distinct, not roughly as numerous as the medium tier.
const PATH_COUNT = 7;
const PULSES_PER_PATH = 1;

export class EnergyPaths {
  constructor(formationData) {
    const { points, colors } = formationData;
    this.curves = [];
    this.pulseSpeeds = [];

    const structural = points.filter((p) => !p.isAmbient);

    // Real bug found from a live screenshot: the old midpoint was the
    // straight a-b line's center plus a small random jitter (+-0.15) --
    // for genuinely far-apart points (>0.55 apart in a ~1-2 unit volume),
    // that jitter is tiny relative to the distance, so the curve barely
    // deviated from a straight line and several paths visibly cut across
    // empty exterior space like stray scratches, disconnected from the
    // particle mass. Fixed by snapping each intermediate control point to
    // the NEAREST REAL structural particle to that interpolated position,
    // so the curve actually threads through real density the whole way,
    // matching this class's own original intent (see the file comment).
    const nearestTo = (pos) => {
      let best = null,
        bestD = Infinity;
      for (const p of structural) {
        const d = pos.distanceToSquared(p.target);
        if (d < bestD) {
          bestD = d;
          best = p;
        }
      }
      return best;
    };

    for (let i = 0; i < PATH_COUNT; i++) {
      const a = structural[Math.floor(Math.random() * structural.length)];
      // a point reasonably far from `a` but not the most extreme outlier
      // in the whole volume, so paths stay plausible rather than reaching
      // corner-to-corner across the structure
      let b = a;
      for (let tries = 0; tries < 20; tries++) {
        const candidate = structural[Math.floor(Math.random() * structural.length)];
        const d = candidate.target.distanceTo(a.target);
        if (d > 0.5 && d < 1.0) {
          b = candidate;
          break;
        }
      }

      const rawMid1 = a.target.clone().lerp(b.target, 0.33);
      const rawMid2 = a.target.clone().lerp(b.target, 0.66);
      const mid1 = nearestTo(rawMid1).target;
      const mid2 = nearestTo(rawMid2).target;

      const curve = new THREE.CatmullRomCurve3([a.target.clone(), mid1.clone(), mid2.clone(), b.target.clone()]);
      this.curves.push({ curve, colorA: this._colorAt(a.index, colors), colorB: this._colorAt(b.index, colors) });
      this.pulseSpeeds.push(0.08 + Math.random() * 0.1);
    }

    this._buildTubes();
    this._buildPulses();
  }

  _colorAt(index, colors) {
    return new THREE.Color(colors[index * 3], colors[index * 3 + 1], colors[index * 3 + 2]);
  }

  _buildTubes() {
    const positions = [];
    const lineColors = [];
    const starts = [];
    const durations = [];
    const weights = [];
    const SEGMENTS = 24;

    this.curves.forEach(({ curve, colorA, colorB }, pathIdx) => {
      const pts = curve.getPoints(SEGMENTS);
      for (let i = 0; i < pts.length - 1; i++) {
        positions.push(pts[i].x, pts[i].y, pts[i].z, pts[i + 1].x, pts[i + 1].y, pts[i + 1].z);
        const t0 = i / SEGMENTS;
        const t1 = (i + 1) / SEGMENTS;
        const c0 = colorA.clone().lerp(colorB, t0);
        const c1 = colorA.clone().lerp(colorB, t1);
        lineColors.push(c0.r, c0.g, c0.b, c1.r, c1.g, c1.b);
        // major pathways only become visible late in formation, once the
        // structure they connect has already mostly arrived
        const start = 0.72 + (pathIdx % 5) * 0.02;
        starts.push(start, start);
        durations.push(0.18, 0.18);
        // brightest tier -- above NeuralNetwork's medium weight of 1.0
        weights.push(1.6, 1.6);
      }
    });

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
    geometry.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(lineColors), 3));
    geometry.setAttribute("aLineStart", new THREE.BufferAttribute(new Float32Array(starts), 1));
    geometry.setAttribute("aLineDuration", new THREE.BufferAttribute(new Float32Array(durations), 1));
    geometry.setAttribute("aWeight", new THREE.BufferAttribute(new Float32Array(weights), 1));

    this.uniforms = { uFormProgress: { value: 0 }, uOpacity: { value: 0.75 } };
    const material = new THREE.ShaderMaterial({
      vertexShader: lineVertexShader,
      fragmentShader: lineFragmentShader,
      uniforms: this.uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    this.tubes = new THREE.LineSegments(geometry, material);
  }

  _buildPulses() {
    const count = this.curves.length * PULSES_PER_PATH;
    const positions = new Float32Array(count * 3);
    const pulseColors = new Float32Array(count * 3);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(pulseColors, 3));
    const material = new THREE.PointsMaterial({
      size: 0.035,
      vertexColors: true,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    this.pulses = new THREE.Points(geometry, material);
    this._pulseMaterial = material;
  }

  update(time, formProgress) {
    this.uniforms.uFormProgress.value = formProgress;
    const posAttr = this.pulses.geometry.getAttribute("position");
    const colorAttr = this.pulses.geometry.getAttribute("color");
    this._pulseMaterial.opacity = THREE.MathUtils.smoothstep(formProgress, 0.75, 0.95) * 0.9;

    this.curves.forEach(({ curve, colorA, colorB }, i) => {
      const t = (time * this.pulseSpeeds[i] + i * 0.31) % 1;
      const p = curve.getPointAt(t);
      posAttr.setXYZ(i, p.x, p.y, p.z);
      const c = colorA.clone().lerp(colorB, t);
      colorAttr.setXYZ(i, c.r, c.g, c.b);
    });
    posAttr.needsUpdate = true;
    colorAttr.needsUpdate = true;
  }
}
