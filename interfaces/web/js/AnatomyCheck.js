// Milestone 1 ONLY: display the real anatomical base mesh, nothing else.
// No particles, no branches, no colors/glow, no pedestal, no animation,
// no dashboard, no card UI. Explicit instruction: validate the anatomy
// before building anything on top of it.
//
// The mesh itself is NOT procedurally invented -- it's real MRI-derived
// human brain geometry (left + right cerebral hemisphere, public domain,
// NIH 3D / UCSF-UCSD "glassbrain" project, entries 3DPX-000757/000758).
// This file's only job is: load both halves, position them correctly
// relative to each other, light them so the real anatomy is visible, and
// frame them responsively. See interfaces/web/assets/brain/README.md for
// the exact source URLs and license.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";
import { GLTFLoader } from "https://cdn.jsdelivr.net/npm/three@0.160/examples/jsm/loaders/GLTFLoader.js";

const LEFT_URL = "/web/assets/brain/lh_NIH3D.glb";
const RIGHT_URL = "/web/assets/brain/rh_NIH3D.glb";

// Real fissure gap between the two hemispheres, in the same units as the
// source meshes (millimeters, typical for MRI-derived data) -- narrow
// relative to real brain scale (~140mm wide), just enough to visibly
// separate the two halves rather than let them intersect if their own
// centroids both sit at x=0.
const FISSURE_GAP_MM = 2.5;

export class AnatomyCheck {
  constructor(container) {
    this.container = container;
    this.scene = new THREE.Scene();

    // Real bug hit twice building the other Empire Brain page: a
    // container can have zero layout size at construction time (a
    // backgrounded/not-yet-visible tab), and initializing the renderer
    // at 0x0 leaves the canvas permanently broken since resize only
    // fires on a real size CHANGE. Fallback size plus a visibilitychange
    // listener (in _bindResize below) fixes it for good this time.
    const FALLBACK_W = 900,
      FALLBACK_H = 700;
    const w = container.clientWidth || FALLBACK_W;
    const h = container.clientHeight || FALLBACK_H;
    this.camera = new THREE.PerspectiveCamera(35, w / Math.max(h, 1), 1, 5000);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h);
    this.renderer.setClearColor(0x05070a, 1); // plain dark background, per spec
    container.appendChild(this.renderer.domElement);

    // Neutral clay-style lighting so the real anatomy (curvature, sulci/
    // gyri, hemisphere separation) reads clearly by shading alone -- no
    // color scheme yet, that's explicitly deferred to a later milestone.
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.55));
    const key = new THREE.DirectionalLight(0xffffff, 1.1);
    key.position.set(1, 1.2, 1.5);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0x8fb3ff, 0.35);
    fill.position.set(-1.2, 0.4, -1);
    this.scene.add(fill);
    const rim = new THREE.DirectionalLight(0xffffff, 0.4);
    rim.position.set(0, 1, -2);
    this.scene.add(rim);

    this.brainGroup = new THREE.Group();
    this.scene.add(this.brainGroup);

    this._neutralMaterial = new THREE.MeshStandardMaterial({
      color: 0xc9cdd6,
      roughness: 0.55,
      metalness: 0.03,
    });

    this._loaded = { left: null, right: null };
    this._loadHemisphere(LEFT_URL, "left");
    this._loadHemisphere(RIGHT_URL, "right");

    window.addEventListener("resize", () => this._onResize());
    // Catches the "container size never changes, so resize never fires
    // again" case -- a tab that loaded hidden, then becomes visible later
    // with the exact same layout size it always had.
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") this._onResize();
    });
    this._loop = this._loop.bind(this);
    requestAnimationFrame(this._loop);
  }

  _loadHemisphere(url, side) {
    const loader = new GLTFLoader();
    loader.load(
      url,
      (gltf) => {
        const root = gltf.scene;
        // Real bug found from live bounding-box measurement, not
        // assumed: this source data's own up-axis isn't Three.js's Y-up.
        // Before this rotation, the combined bounding box measured
        // 147x178x110mm (width x "Y" x "Z") -- a real brain is roughly
        // 140mm wide x 167mm front-to-back x 93mm tall, so the 178mm
        // span was clearly the anterior-posterior axis mislabeled as
        // height, and the 110mm span was the real vertical extent.
        // Rotating -90 deg about X maps the file's Z (true vertical,
        // mostly-positive extent -- the mesh's local origin sits near
        // the brain's base) onto Three.js's Y-up, and its Y onto Z
        // (front/back, sign flipped by the same rotation).
        root.rotation.x = -Math.PI / 2;
        // Override whatever baked material the source file carries --
        // this milestone is anatomy only, explicitly no color yet.
        root.traverse((child) => {
          if (child.isMesh) {
            child.material = this._neutralMaterial;
            child.castShadow = false;
            child.receiveShadow = false;
          }
        });
        this._loaded[side] = root;
        this.brainGroup.add(root);
        if (this._loaded.left && this._loaded.right) this._alignAndFrame();
      },
      undefined,
      (err) => console.error(`AnatomyCheck: failed to load ${side} hemisphere`, err)
    );
  }

  /** Centers each hemisphere on its own midline face and separates them
   * by a small real fissure gap, then frames the camera on the combined
   * result -- real measured bounding boxes, not assumed offsets (the
   * exact lesson learned the hard way earlier building this brain: never
   * assume where two pieces of geometry meet, measure it). */
  _alignAndFrame() {
    const left = this._loaded.left;
    const right = this._loaded.right;

    const leftBox = new THREE.Box3().setFromObject(left);
    const rightBox = new THREE.Box3().setFromObject(right);

    // Each hemisphere's own medial (midline) face is its innermost X
    // extent. Left hemisphere sits on the -X side in real anatomical
    // convention here (its mesh's own max-X edge is the midline); right
    // hemisphere's min-X edge is its midline. Shift each so that edge
    // sits at +-(gap/2) from x=0.
    const leftMedialX = leftBox.max.x;
    const rightMedialX = rightBox.min.x;
    left.position.x += -FISSURE_GAP_MM / 2 - leftMedialX;
    right.position.x += FISSURE_GAP_MM / 2 - rightMedialX;

    // Align both hemispheres' vertical/depth centers to each other (real
    // MRI segmentations of the same subject should already match, but
    // measure rather than assume in case the two source files use
    // slightly different local origins).
    const leftBox2 = new THREE.Box3().setFromObject(left);
    const rightBox2 = new THREE.Box3().setFromObject(right);
    const leftCenter = leftBox2.getCenter(new THREE.Vector3());
    const rightCenter = rightBox2.getCenter(new THREE.Vector3());
    right.position.y += leftCenter.y - rightCenter.y;
    right.position.z += leftCenter.z - rightCenter.z;

    // Center the WHOLE combined brain in the group so responsive framing
    // (below) always orbits/fits around its true centroid.
    const combined = new THREE.Box3().setFromObject(this.brainGroup);
    const center = combined.getCenter(new THREE.Vector3());
    this.brainGroup.position.sub(center);

    this._combinedSize = combined.getSize(new THREE.Vector3());
    this._frameCamera();
  }

  /** Fits the camera distance to the real measured bounding size so the
   * complete brain fits on screen at any aspect ratio without distorting
   * proportions -- refit on every resize, not just once at load. */
  _frameCamera() {
    if (!this._combinedSize) return;
    const { clientWidth: w, clientHeight: h } = this.container;
    this.camera.aspect = w / Math.max(h, 1);

    const size = this._combinedSize;
    const maxDim = Math.max(size.x, size.y, size.z);
    const fovRad = (this.camera.fov * Math.PI) / 180;
    // distance needed so maxDim fits within the SMALLER of the two
    // screen-space extents (whichever the current aspect ratio
    // constrains more), with real margin -- this is what keeps
    // proportions intact across very wide or very tall viewports instead
    // of stretching/cropping the brain.
    const vFit = maxDim / 2 / Math.tan(fovRad / 2);
    const hFit = vFit / this.camera.aspect;
    const distance = Math.max(vFit, hFit) * 1.35;

    // Reference framing: slightly above center, looking down and
    // slightly toward the front -- the same primary 3/4 angle the
    // supplied reference uses, not a flat front-on view.
    this.camera.position.set(distance * 0.18, distance * 0.32, distance * 0.92);
    this.camera.lookAt(0, size.y * 0.05, 0);
    this.camera.updateProjectionMatrix();
  }

  _onResize() {
    const { clientWidth: w, clientHeight: h } = this.container;
    if (w === 0 || h === 0) return;
    this.renderer.setSize(w, h);
    this._frameCamera();
  }

  _loop() {
    requestAnimationFrame(this._loop);
    this.renderer.render(this.scene, this.camera);
  }
}
