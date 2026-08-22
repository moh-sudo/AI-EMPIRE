// Top-level orchestrator: owns the THREE.Scene/Camera/Renderer, wires the
// other modules together, and runs the render loop. This is the only file
// that knows about all the others -- BrainFormationEngine doesn't know
// about NeuralParticleSystem, NeuralNetwork doesn't know about EnergyPaths,
// etc. Exposes a small public API (setState, pulseHealth) on the mounted
// instance so the existing card-UI script (division list, live status
// polling) can react to real events without needing to know anything
// about Three.js.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";
import { EffectComposer } from "https://cdn.jsdelivr.net/npm/three@0.160/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "https://cdn.jsdelivr.net/npm/three@0.160/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "https://cdn.jsdelivr.net/npm/three@0.160/examples/jsm/postprocessing/UnrealBloomPass.js";
import { BrainFormationEngine } from "./BrainFormationEngine.js";
import { NeuralParticleSystem } from "./NeuralParticleSystem.js";
import { NeuralNetwork } from "./NeuralNetwork.js";
import { EnergyPaths } from "./EnergyPaths.js";
import { Pedestal } from "./Pedestal.js";
import { BrainStateMachine, BrainState } from "./BrainStateMachine.js";

const FORM_DURATION_S = 5.5;

export class EmpireBrain {
  constructor(container) {
    this.container = container;
    this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.clock = new THREE.Clock();
    this.elapsed = 0;
    this.formProgress = 0;
    this._healthPulse = 0;

    this._initScene();
    this._buildBrain();
    this._bindResize();
    this._loop = this._loop.bind(this);
    requestAnimationFrame(this._loop);
  }

  _initScene() {
    // Real bug found live: if the container has zero layout size at
    // construction time (page not yet visible/painted -- can happen on a
    // background tab, and is exactly what this session's own preview pane
    // hit), renderer.setSize(0,0) leaves the canvas permanently 0x0 --
    // ResizeObserver only fires on a size CHANGE, so it never fires again
    // once the tab becomes visible if the container's size doesn't
    // actually change. Falls back to a sane default here, and the
    // visibilitychange listener in _bindResize re-applies the real size
    // once the page is actually visible.
    const FALLBACK_W = 800,
      FALLBACK_H = 640;
    const w = this.container.clientWidth || FALLBACK_W;
    const h = this.container.clientHeight || FALLBACK_H;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, w / Math.max(h, 1), 0.1, 10);
    // Pulled back / lowered slightly from the first pass: gl.readPixels
    // showed the pedestal (y=-0.97) sitting right at the edge of the
    // visible frustum and getting clipped at the bottom. This framing
    // leaves real margin above the hemispheres and below the pedestal,
    // verified the same way rather than assumed.
    this.camera.position.set(0, 0.0, 2.75);
    this.camera.lookAt(0, -0.15, 0);

    // Real regression found live: UnrealBloomPass's composite shader
    // writes alpha=1 across the WHOLE frame, not just where something was
    // actually drawn -- confirmed via gl.readPixels on a definitely-empty
    // corner reading alpha=255. A transparent canvas (the first pass's
    // approach, letting the panel's own CSS gradient show through) doesn't
    // survive bloom without extra alpha-preservation work. Simplest robust
    // fix: render opaque with a clear color matching the panel's own
    // --void token instead of fighting the bloom pass's alpha handling --
    // visually near-identical here since the panel's background is
    // already a subtle, mostly-flat near-black gradient.
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h);
    this.renderer.setClearColor(0x030405, 1);
    this.container.appendChild(this.renderer.domElement);

    this.group = new THREE.Group();
    // brain sits right-of-center in the panel, leaving room for the left
    // column cards, matching this display's established composition
    this.group.position.x = 0.55;
    this.scene.add(this.group);

    // Real bloom, requested explicitly ("subtle bloom around brightest
    // pathways"), not a shader trick. Threshold kept fairly high (0.4) and
    // strength modest (0.45) deliberately -- the LAST time brightness got
    // tuned carelessly here (the gl_PointSize bug), it blew out 90% of the
    // canvas to white; a high threshold means only genuinely bright pixels
    // (particle cores, pulses) bloom, not the whole faint mesh.
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    // Radius/threshold retuned after a real gl.readPixels check: 0.35
    // radius let bloom haze bleed across the ENTIRE canvas, even a
    // definitely-empty corner (background read as rgb(28,34,38) instead
    // of the near-black clear color) -- tighter radius and a higher
    // threshold keep it contained to actually-bright points instead of a
    // uniform glow wash.
    this.bloomPass = new UnrealBloomPass(new THREE.Vector2(w, h), 0.4, 0.22, 0.5);
    this.composer.addPass(this.bloomPass);
  }

  /** canvasHeight / (2*tan(fov/2)) -- the real perspective-projection
   * constant that converts a world-space point size into screen pixels at
   * distance 1, per ParticleShader.js's gl_PointSize formula. Must be
   * recomputed whenever the canvas resizes or the fov changes. */
  _computeSizeAttenuation() {
    const fovRad = (this.camera.fov * Math.PI) / 180;
    return this.renderer.domElement.height / (2 * Math.tan(fovRad / 2));
  }

  _buildBrain() {
    this.formationEngine = new BrainFormationEngine({});
    const data = this.formationEngine.generate();

    this.particleSystem = new NeuralParticleSystem(data);
    this.neuralNetwork = new NeuralNetwork(data);
    this.energyPaths = new EnergyPaths(data);
    this.pedestal = new Pedestal();
    this.stateMachine = new BrainStateMachine(BrainState.IDLE);

    this.group.add(this.particleSystem.points);
    this.group.add(this.neuralNetwork.lines);
    this.group.add(this.energyPaths.tubes);
    this.group.add(this.energyPaths.pulses);
    this.group.add(this.pedestal.group);

    this.particleSystem.setSizeAttenuation(this._computeSizeAttenuation());
  }

  _bindResize() {
    this._resizeObserver = new ResizeObserver(() => this._onResize());
    this._resizeObserver.observe(this.container);
    // Catches the "container size never changes, so ResizeObserver never
    // fires again" case: a tab that loaded hidden, then becomes visible
    // later with the exact same layout size it always had.
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") this._onResize();
    });
  }

  _onResize() {
    const { clientWidth: w, clientHeight: h } = this.container;
    if (w === 0 || h === 0) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.composer.setSize(w, h);
    this.particleSystem.setSizeAttenuation(this._computeSizeAttenuation());
  }

  /** Public API: called by the card-UI script's empire-status poller on a
   * successful refresh -- a brief brightness pulse across the whole
   * structure, honestly tied to a real event rather than decorative. */
  pulseHealth() {
    this._healthPulse = 1;
  }

  setState(state) {
    this.stateMachine.setState(state);
  }

  _loop() {
    requestAnimationFrame(this._loop);
    const dt = Math.min(this.clock.getDelta(), 0.05);

    // formation only needs to run once; after that, freeze uTime under
    // reduced motion so idle jitter/breathing/rotation/pulses stop, while
    // the already-formed structure stays fully visible
    const stillForming = this.formProgress < 1;
    if (!this.reducedMotion || stillForming) {
      this.elapsed += dt;
    }
    this.formProgress = Math.min(1, this.elapsed / FORM_DURATION_S);

    this._healthPulse = Math.max(0, this._healthPulse - dt * 1.2);
    const params = this.stateMachine.update(dt);

    this.particleSystem.setPointScale(params.pointScale);
    this.particleSystem.update(this.elapsed, this.formProgress, this._healthPulse * params.pulseIntensity);
    this.neuralNetwork.update(this.formProgress);
    this.neuralNetwork.uniforms.uOpacity.value = params.lineOpacity;
    this.energyPaths.update(this.elapsed, this.formProgress);
    this.pedestal.update(this.elapsed, this.formProgress, this._healthPulse * params.pulseIntensity);

    if (!this.reducedMotion) {
      this.group.rotation.y = Math.sin(this.elapsed * 0.08) * 0.18 + this.elapsed * params.rotateSpeed * 0.02;
    }

    this.composer.render();
  }

  dispose() {
    this._resizeObserver?.disconnect();
    this.renderer.dispose();
  }
}

export { BrainState };
