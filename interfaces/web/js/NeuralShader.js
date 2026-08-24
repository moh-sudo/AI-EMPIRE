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
    // Real bug found from a live screenshot: the old formula
    // (vColor * (0.7 + weight*0.5)) multiplies color channels by up to
    // 1.5x for high-weight edges -- most division hex colors already have
    // one or two near-maxed channels, so that pushed them straight to
    // clipped white. That's exactly why the major pathways (highest
    // weight) rendered as a stark white wireframe instead of showing
    // their real color. Capped at 1.0 so it can only ever desaturate
    // low-weight filaments toward black, never blow high-weight ones out
    // to white; opacity (not color) carries the "how prominent" signal.
    float brightness = clamp(0.45 + vWeight * 0.35, 0.0, 1.0);
    float alpha = vAlpha * uOpacity * clamp(vWeight, 0.0, 1.0);
    gl_FragColor = vec4(vColor * brightness, alpha);
  }
`;
