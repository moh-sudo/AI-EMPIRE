// The futuristic circular base the brainstem connects into: concentric
// glowing rings with a slow rotation, synchronized to the brain's own
// pulse via the same uHealthPulse-style brightness bump. The circulating
// particles around it are generated as part of BrainFormationEngine's
// pedestal-orbit particles and rendered by NeuralParticleSystem -- this
// class owns only the ring geometry.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";

const RING_RADII = [0.36, 0.5, 0.64];
const RING_Y = -0.97;
const RING_COLOR = 0xffc24b;

export class Pedestal {
  constructor() {
    this.group = new THREE.Group();
    this.rings = [];

    RING_RADII.forEach((radius, i) => {
      const geometry = new THREE.RingGeometry(radius - 0.006, radius, 96);
      const material = new THREE.MeshBasicMaterial({
        color: RING_COLOR,
        transparent: true,
        opacity: 0.45 - i * 0.1,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.y = RING_Y;
      this.group.add(mesh);
      this.rings.push({ mesh, material, baseOpacity: material.opacity, speed: 0.06 + i * 0.03 * (i % 2 === 0 ? 1 : -1) });
    });

    const glowGeo = new THREE.CircleGeometry(RING_RADII[RING_RADII.length - 1] * 0.9, 48);
    const glowMat = new THREE.MeshBasicMaterial({
      color: RING_COLOR,
      transparent: true,
      opacity: 0.06,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.glow = new THREE.Mesh(glowGeo, glowMat);
    this.glow.rotation.x = -Math.PI / 2;
    this.glow.position.y = RING_Y - 0.001;
    this.group.add(this.glow);
  }

  update(time, formProgress, healthPulse = 0) {
    const visible = THREE.MathUtils.smoothstep(formProgress, 0.15, 0.4);
    this.rings.forEach((r) => {
      r.mesh.rotation.z = time * r.speed;
      r.material.opacity = r.baseOpacity * visible * (1 + healthPulse * 0.5);
    });
    this.glow.material.opacity = 0.06 * visible * (1 + Math.sin(time * 0.5) * 0.3);
  }
}
