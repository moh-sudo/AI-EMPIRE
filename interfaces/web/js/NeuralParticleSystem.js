// Layer 1 (+5, ambient, + pedestal orbit): the actual particle cloud,
// rendered as ONE THREE.Points draw call via BufferGeometry/instanced
// attributes -- not thousands of individual meshes. All formation/idle
// motion happens on the GPU in ParticleShader; this class only builds the
// geometry once and updates two uniforms per frame.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";
import { particleVertexShader, particleFragmentShader } from "./ParticleShader.js";

export class NeuralParticleSystem {
  constructor(formationData) {
    const { count, starts, targets, colors, startTimes, durations, sizes, phases, orbitRadius, orbitY, orbitSpeed } =
      formationData;

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(targets, 3)); // for bounding-sphere/frustum purposes
    geometry.setAttribute("aStart", new THREE.BufferAttribute(starts, 3));
    geometry.setAttribute("aTarget", new THREE.BufferAttribute(targets, 3));
    geometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute("aStartTime", new THREE.BufferAttribute(startTimes, 1));
    geometry.setAttribute("aDuration", new THREE.BufferAttribute(durations, 1));
    geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
    geometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
    geometry.setAttribute("aOrbitRadius", new THREE.BufferAttribute(orbitRadius, 1));
    geometry.setAttribute("aOrbitY", new THREE.BufferAttribute(orbitY, 1));
    geometry.setAttribute("aOrbitSpeed", new THREE.BufferAttribute(orbitSpeed, 1));
    geometry.computeBoundingSphere();

    this.uniforms = {
      uTime: { value: 0 },
      uFormProgress: { value: 0 },
      uPointScale: { value: 1 },
      uHealthPulse: { value: 0 },
      uSizeAttenuation: { value: 900 }, // real value set by EmpireBrain from the actual camera/canvas
    };

    const material = new THREE.ShaderMaterial({
      vertexShader: particleVertexShader,
      fragmentShader: particleFragmentShader,
      uniforms: this.uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    this.points = new THREE.Points(geometry, material);
    this.count = count;
  }

  update(time, formProgress, healthPulse = 0) {
    this.uniforms.uTime.value = time;
    this.uniforms.uFormProgress.value = formProgress;
    this.uniforms.uHealthPulse.value = healthPulse;
  }

  setPointScale(scale) {
    this.uniforms.uPointScale.value = scale;
  }

  setSizeAttenuation(value) {
    this.uniforms.uSizeAttenuation.value = value;
  }
}
