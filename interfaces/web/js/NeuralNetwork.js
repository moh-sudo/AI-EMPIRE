// Layer 2: short-range neural connections between nearby particles.
// Nearest-neighbor search uses a 3D uniform grid (cell = MAX_LINK_DIST)
// rather than checking every point against every other point -- at ~8.4k
// structural points an O(n^2) scan is real, avoidable slowness (the same
// fix the earlier 2D version needed once its own density grew).

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";
import { lineVertexShader, lineFragmentShader } from "./NeuralShader.js";

const MAX_LINK_DIST = 0.09;
const LINKS_PER_NODE = 2;

export class NeuralNetwork {
  constructor(formationData) {
    const { points, colors, startTimes, durations } = formationData;

    const grid = new Map();
    const cellKey = (x, y, z) => `${x}_${y}_${z}`;
    const cellOf = (p) => [Math.floor(p.x / MAX_LINK_DIST), Math.floor(p.y / MAX_LINK_DIST), Math.floor(p.z / MAX_LINK_DIST)];

    for (const pt of points) {
      const [cx, cy, cz] = cellOf(pt.target);
      const key = cellKey(cx, cy, cz);
      if (!grid.has(key)) grid.set(key, []);
      grid.get(key).push(pt);
    }

    const positions = [];
    const lineColors = [];
    const lineStarts = [];
    const lineDurations = [];
    const lineWeights = [];
    const seenPairs = new Set();
    const tmp = new THREE.Vector3();

    for (const pt of points) {
      const [cx, cy, cz] = cellOf(pt.target);
      const candidates = [];
      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          for (let dz = -1; dz <= 1; dz++) {
            const bucket = grid.get(cellKey(cx + dx, cy + dy, cz + dz));
            if (!bucket) continue;
            for (const other of bucket) {
              if (other === pt) continue;
              const d = tmp.subVectors(pt.target, other.target).length();
              if (d < MAX_LINK_DIST) candidates.push([d, other]);
            }
          }
        }
      }
      candidates.sort((a, b) => a[0] - b[0]);
      // Real hierarchy instead of every connection carrying equal weight:
      // the nearest neighbor is always a faint "micro" filament; the
      // second-nearest is only kept ~30% of the time and rendered as a
      // brighter "medium" pathway when it is -- sparse and organically
      // distributed, not a uniform grid of identical lines.
      for (let k = 0; k < Math.min(LINKS_PER_NODE, candidates.length); k++) {
        const isMedium = k === 1;
        if (isMedium && Math.random() > 0.3) continue;
        const other = candidates[k][1];
        const key = pt.index < other.index ? `${pt.index}_${other.index}` : `${other.index}_${pt.index}`;
        if (seenPairs.has(key)) continue;
        seenPairs.add(key);

        positions.push(pt.target.x, pt.target.y, pt.target.z, other.target.x, other.target.y, other.target.z);
        lineColors.push(
          colors[pt.index * 3],
          colors[pt.index * 3 + 1],
          colors[pt.index * 3 + 2],
          colors[other.index * 3],
          colors[other.index * 3 + 1],
          colors[other.index * 3 + 2]
        );
        const start = Math.max(startTimes[pt.index], startTimes[other.index]);
        const dur = Math.max(durations[pt.index], durations[other.index]);
        lineStarts.push(start, start);
        lineDurations.push(dur, dur);
        const weight = isMedium ? 1.0 : 0.4;
        lineWeights.push(weight, weight);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
    geometry.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(lineColors), 3));
    geometry.setAttribute("aLineStart", new THREE.BufferAttribute(new Float32Array(lineStarts), 1));
    geometry.setAttribute("aLineDuration", new THREE.BufferAttribute(new Float32Array(lineDurations), 1));
    geometry.setAttribute("aWeight", new THREE.BufferAttribute(new Float32Array(lineWeights), 1));

    this.uniforms = { uFormProgress: { value: 0 }, uOpacity: { value: 0.35 } };
    const material = new THREE.ShaderMaterial({
      vertexShader: lineVertexShader,
      fragmentShader: lineFragmentShader,
      uniforms: this.uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    this.lines = new THREE.LineSegments(geometry, material);
  }

  update(formProgress) {
    this.uniforms.uFormProgress.value = formProgress;
  }
}
