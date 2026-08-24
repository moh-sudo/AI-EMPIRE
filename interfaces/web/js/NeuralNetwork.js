// Layer 2 (and the fine cortical mesh): renders the REAL tree edges from
// BrainFormationEngine's space-colonization growth directly -- no
// nearest-neighbor guessing needed anymore, since every edge is already a
// genuine parent-child connection from the growth process. Weight (micro
// vs. medium brightness) comes from tree depth: shallow edges near the
// trunks render brighter/thicker, deep edges near the cortex render as
// faint fine filaments -- a real hierarchy, not a uniform mesh.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";
import { lineVertexShader, lineFragmentShader } from "./NeuralShader.js";

export class NeuralNetwork {
  constructor(formationData) {
    const { treeNodes, treeEdges, colors, startTimes, durations } = formationData;

    const positions = [];
    const lineColors = [];
    const lineStarts = [];
    const lineDurations = [];
    const lineWeights = [];

    for (const e of treeEdges) {
      const a = treeNodes[e.a],
        b = treeNodes[e.b];
      positions.push(a.pos.x, a.pos.y, a.pos.z, b.pos.x, b.pos.y, b.pos.z);
      lineColors.push(
        colors[e.a * 3],
        colors[e.a * 3 + 1],
        colors[e.a * 3 + 2],
        colors[e.b * 3],
        colors[e.b * 3 + 1],
        colors[e.b * 3 + 2]
      );
      const start = Math.max(startTimes[e.a], startTimes[e.b]);
      const dur = Math.max(durations[e.a], durations[e.b]);
      lineStarts.push(start, start);
      lineDurations.push(dur, dur);
      // shallow depth (near the trunks) = heavier weight/brighter; deep
      // (near the cortex) = fine, faint filaments
      const depthFrac = Math.min(1, b.depth / 24);
      const weight = THREE.MathUtils.lerp(1.1, 0.28, depthFrac);
      lineWeights.push(weight, weight);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
    geometry.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(lineColors), 3));
    geometry.setAttribute("aLineStart", new THREE.BufferAttribute(new Float32Array(lineStarts), 1));
    geometry.setAttribute("aLineDuration", new THREE.BufferAttribute(new Float32Array(lineDurations), 1));
    geometry.setAttribute("aWeight", new THREE.BufferAttribute(new Float32Array(lineWeights), 1));

    this.uniforms = { uFormProgress: { value: 0 }, uOpacity: { value: 0.4 } };
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
