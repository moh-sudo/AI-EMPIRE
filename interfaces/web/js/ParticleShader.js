// GPU-driven particle shader for NeuralParticleSystem. The formation
// animation (scattered -> brain position) and the idle jitter/breathing
// both happen in the VERTEX shader, driven by uniforms (uFormProgress,
// uTime) -- not by CPU-side per-frame attribute updates. At ~9k particles
// that's the difference between one cheap GPU pass and a JS loop touching
// 27k floats every frame.

export const particleVertexShader = `
  attribute vec3 aStart;
  attribute vec3 aTarget;
  attribute vec3 aColor;
  attribute float aStartTime;
  attribute float aDuration;
  attribute float aSize;
  attribute float aPhase;
  attribute float aOrbitRadius; // > 0 marks this particle as a pedestal-orbit particle
  attribute float aOrbitY;
  attribute float aOrbitSpeed;

  uniform float uTime;
  uniform float uFormProgress;
  uniform float uPointScale;
  uniform float uHealthPulse; // 0..1, brief brightness pulse when empire-status refreshes
  // canvasHeight / (2 * tan(fov/2)) -- computed once in JS (EmpireBrain.js)
  // from the real camera/canvas, not guessed. aSize is a small WORLD-space
  // diameter (~0.006-0.014 units); this converts it to real screen pixels
  // via perspective attenuation. A first pass used a bare constant here
  // instead of this real derivation and produced ~220px-diameter points --
  // confirmed live via gl.readPixels showing 90% of the canvas lit up
  // near-white before this fix.
  uniform float uSizeAttenuation;

  varying vec3 vColor;
  varying float vAlpha;

  float easeOutCubic(float t) { return 1.0 - pow(1.0 - t, 3.0); }

  void main() {
    float localT = clamp((uFormProgress - aStartTime) / max(aDuration, 0.0001), 0.0, 1.0);
    float e = easeOutCubic(localT);

    vec3 pos;
    if (aOrbitRadius > 0.0) {
      // pedestal-ring orbit particles -- circle continuously once formed.
      // Per feedback, a subset should periodically rise from the pedestal
      // toward the brainstem rather than just circling in place -- a cheap
      // sawtooth on top of the orbit, GPU-driven, no extra particle system.
      float ang = uTime * aOrbitSpeed + aPhase * 6.2831853;
      float cycle = fract(uTime * 0.09 + aPhase);
      float rise = (aPhase > 0.6) ? smoothstep(0.0, 0.7, cycle) * (1.0 - smoothstep(0.7, 1.0, cycle)) * 0.55 : 0.0;
      float shrink = 1.0 - rise * 0.7; // spiral inward while rising, toward the brainstem's own radius
      vec3 orbitTarget = vec3(cos(ang) * aOrbitRadius * shrink, aOrbitY + rise, sin(ang) * aOrbitRadius * shrink);
      pos = mix(aStart, orbitTarget, e);
    } else {
      pos = mix(aStart, aTarget, e);
      // idle jitter + slow breathing, only once mostly formed -- subtle,
      // not the whole structure constantly shaking.
      float settle = smoothstep(0.82, 1.0, uFormProgress) * localT;
      pos += settle * vec3(
        sin(uTime * 0.55 + aPhase * 6.2831853) * 0.012,
        cos(uTime * 0.63 + aPhase * 9.1) * 0.012,
        sin(uTime * 0.47 + aPhase * 4.6) * 0.012
      );
      float breathe = 1.0 + 0.012 * sin(uTime * 0.35) * settle;
      pos *= breathe;
    }

    vColor = aColor * (1.0 + uHealthPulse * 0.6);
    vAlpha = localT;

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = aSize * uPointScale * uSizeAttenuation / max(-mvPosition.z, 0.001);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

export const particleFragmentShader = `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec2 uv = gl_PointCoord - vec2(0.5);
    float d = length(uv);
    if (d > 0.5) discard;
    float core = smoothstep(0.5, 0.0, d);
    float glow = smoothstep(0.5, 0.15, d) * 0.5;
    float alpha = (core * 0.85 + glow) * vAlpha;
    gl_FragColor = vec4(vColor, alpha);
  }
`;
