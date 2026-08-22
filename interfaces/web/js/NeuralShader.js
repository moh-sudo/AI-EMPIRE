// Shared line shader for NeuralNetwork (short-range connections) and
// EnergyPaths (major pathways). Fade-in timing is baked per-vertex at
// geometry build time (aLineStart/aLineDuration -- the later of the two
// endpoints' own particle timings), so connections visibly snap in only
// once both endpoints they join have actually arrived.

export const lineVertexShader = `
  attribute vec3 aColor;
  attribute float aLineStart;
  attribute float aLineDuration;
  // 0.3ish = a "micro" filament between adjacent particles, 1.0 = a
  // brighter "medium" pathway -- real visual hierarchy instead of every
  // connection carrying equal weight, per direct feedback.
  attribute float aWeight;

  uniform float uFormProgress;

  varying vec3 vColor;
  varying float vAlpha;
  varying float vWeight;

  void main() {
    float t = clamp((uFormProgress - aLineStart) / max(aLineDuration, 0.0001), 0.0, 1.0);
    vColor = aColor;
    vAlpha = t;
    vWeight = aWeight;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

export const lineFragmentShader = `
  uniform float uOpacity;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vWeight;

  void main() {
    gl_FragColor = vec4(vColor * (0.7 + vWeight * 0.5), vAlpha * uOpacity * vWeight);
  }
`;
