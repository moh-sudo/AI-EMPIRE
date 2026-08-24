// Layer 3 (major pathways) + Layer 4 (traveling pulses that branch at real
// junctions). BrainFormationEngine's space-colonization growth already
// produces real root-to-leaf chains (rootPaths) -- the longest, deepest
// branches in the tree, walking actual parent links the whole way. Using
// those directly means these pathways are guaranteed to thread through
// real particle density (they ARE the particles' own connective tissue),
// not a synthetic curve fitted between two far-apart points afterward.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";
import { lineVertexShader, lineFragmentShader } from "./NeuralShader.js";

const PULSES_PER_PATH = 1;

export class EnergyPaths {
  constructor(formationData) {
    const { treeNodes, rootPaths, colors } = formationData;
    this.curves = [];
    this.pulseSpeeds = [];

    for (const chain of rootPaths) {
      if (chain.length < 3) continue;
      const pts = chain.map((i) => treeNodes[i].pos.clone());
      const curve = new THREE.CatmullRomCurve3(pts);
      const rootIdx = chain[0],
        leafIdx = chain[chain.length - 1];
      this.curves.push({ curve, colorA: this._colorAt(rootIdx, colors), colorB: this._colorAt(leafIdx, colors) });
      this.pulseSpeeds.push(0.06 + Math.random() * 0.08);
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
    const SEGMENTS = 32;

    this.curves.forEach(({ curve, colorA, colorB }, pathIdx) => {
      const pts = curve.getPoints(SEGMENTS);
      for (let i = 0; i < pts.length - 1; i++) {
        positions.push(pts[i].x, pts[i].y, pts[i].z, pts[i + 1].x, pts[i + 1].y, pts[i + 1].z);
        const t0 = i / SEGMENTS;
        const t1 = (i + 1) / SEGMENTS;
        const c0 = colorA.clone().lerp(colorB, t0);
        const c1 = colorA.clone().lerp(colorB, t1);
        lineColors.push(c0.r, c0.g, c0.b, c1.r, c1.g, c1.b);
        const start = 0.78 + (pathIdx % 5) * 0.015;
        starts.push(start, start);
        durations.push(0.15, 0.15);
        weights.push(1.6, 1.6);
      }
    });

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
    geometry.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(lineColors), 3));
    geometry.setAttribute("aLineStart", new THREE.BufferAttribute(new Float32Array(starts), 1));
    geometry.setAttribute("aLineDuration", new THREE.BufferAttribute(new Float32Array(durations), 1));
    geometry.setAttribute("aWeight", new THREE.BufferAttribute(new Float32Array(weights), 1));

    this.uniforms = { uFormProgress: { value: 0 }, uOpacity: { value: 0.8 } };
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
    const positions = new Float32Array(Math.max(count, 1) * 3);
    const pulseColors = new Float32Array(Math.max(count, 1) * 3);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(pulseColors, 3));
    const material = new THREE.PointsMaterial({
      size: 0.04,
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
    if (!this.curves.length) return;
    const posAttr = this.pulses.geometry.getAttribute("position");
    const colorAttr = this.pulses.geometry.getAttribute("color");
    this._pulseMaterial.opacity = THREE.MathUtils.smoothstep(formProgress, 0.8, 0.97) * 0.9;

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
