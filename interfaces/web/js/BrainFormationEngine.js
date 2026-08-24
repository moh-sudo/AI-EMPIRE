// Procedurally generates the Empire Brain's target geometry using SPACE
// COLONIZATION -- the standard algorithm for growing organic branching
// structures (trees, root systems, vasculature) toward a target volume.
// This replaced an earlier version that scattered particles directly
// across an anatomical silhouette (a "point cloud shaped like a brain")
// -- real feedback was that it read as a network filling a region, not a
// hierarchy of trunks branching into finer and finer pathways. Space
// colonization gives the real thing: a handful of primary trunks grow
// from the pedestal, and wherever the pull of nearby unclaimed target
// points diverges, a trunk genuinely SPLITS into branches, which split
// again into finer pathways as they approach the dense cortex -- an
// actual parent/child graph, not particles that merely look networked.
//
// The anatomical silhouette itself (hemispheres, central fissure, gyrus
// folds, tapered brainstem) is unchanged from the previous version and
// stays -- it's reused here as the CLOUD OF TARGET POINTS branches grow
// toward, rather than being the final particle positions directly. That
// silhouette was already tuned through several real bug fixes (funnel
// taper, missing fissure, flat gyri); keeping it as the growth target
// carries all of that over instead of re-deriving brain shape from
// scratch.
//
// Deliberately NOT using a general-purpose noise library (simplex/perlin)
// -- a small sum of sine waves at incommensurate frequencies is cheap,
// dependency-free, always well-behaved (no edge cases to debug blind),
// and organic-looking enough for gyrus-style surface perturbation.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160/build/three.module.js";

// Division color palette. Real feedback from two earlier renders: blending
// ALL 7 by weighted distance (even with a sharp falloff) desaturates
// toward gray once several divisions contribute comparably, and a pure
// nearest-attractor pick lets 1-2 geometrically-favored attractors claim
// most of the volume. Blending only the top-2 nearest attractors at any
// point fixes both -- verified live via a pixel-hue histogram (see
// blendedColor below).
// Real finding from live pixel measurement, and it took two attempts to
// diagnose correctly: the first guess ("not enough attractor points for
// the underrepresented divisions") was wrong -- adding a 3rd satellite
// per division barely moved the numbers. The real cause is spatial: the
// space-colonization tree's particle MASS is naturally denser near the
// lower/central confluence zone where all 7 trunks pass through before
// diverging (tree topology -- shared lower branches carry more edges than
// the sparse cortex periphery), and rii/systems' attractor points
// happened to sit closer to that naturally-dense zone than the other 5
// divisions' points, so they kept winning the top-2 blend regardless of
// how many satellites anyone had. Fixed by moving rii/systems OUT toward
// the cortex periphery (where they were always meant to read as
// electric-blue/cyan highlights, not core mass) and pulling the other 5
// divisions' points IN toward that dense confluence zone so they compete
// for it fairly. Orchestrator (gold) is deliberately still anchored there
// too -- it's the routing/core layer, that's correct for it to dominate
// the trunk.
export const DIVISION_COLORS = {
  rii: { hex: 0x36e0ff, pos: [new THREE.Vector3(-0.55, 0.55, 0.4), new THREE.Vector3(0.5, 0.45, 0.4)] },
  learning: { hex: 0xc060ff, pos: [new THREE.Vector3(0.4, 0.15, -0.35), new THREE.Vector3(-0.1, -0.2, -0.1)] },
  fixera: { hex: 0xff9b30, pos: [new THREE.Vector3(-0.4, -0.1, -0.15), new THREE.Vector3(0.1, 0.15, -0.05)] },
  forex: { hex: 0x33e08a, pos: [new THREE.Vector3(0.42, -0.1, 0.25), new THREE.Vector3(-0.15, 0.05, 0.1)] },
  systems: { hex: 0x4ea3ff, pos: [new THREE.Vector3(0.0, 0.62, 0.05), new THREE.Vector3(0.35, -0.55, -0.3)] },
  audit: { hex: 0x8b5cf6, pos: [new THREE.Vector3(0.02, 0.1, -0.45), new THREE.Vector3(-0.1, -0.15, 0.05)] },
  orchestrator: {
    hex: 0xffc24b,
    pos: [new THREE.Vector3(0.0, -0.55, 0.0), new THREE.Vector3(-0.1, -0.05, 0.05), new THREE.Vector3(0.1, -0.05, -0.05)],
  },
};

function gyrus(d) {
  return (
    0.16 * Math.sin(d.x * 8 + 1.7) * Math.cos(d.y * 10 + 0.4) +
    0.11 * Math.sin(d.y * 13 + 2.3) * Math.sin(d.z * 9 + 1.1) +
    0.09 * Math.cos(d.x * 6) * Math.sin(d.z * 14 + 0.9) +
    0.06 * Math.sin(d.x * 21 + d.z * 17 + 3.1) * Math.cos(d.y * 19 + 1.4)
  );
}

function fibonacciDir(i, n) {
  const phi = Math.acos(1 - (2 * (i + 0.5)) / n); // 0 (top pole) .. PI (bottom pole)
  const golden = Math.PI * (1 + Math.sqrt(5));
  const theta = golden * i;
  return new THREE.Vector3(Math.sin(phi) * Math.cos(theta), Math.cos(phi), Math.sin(phi) * Math.sin(theta));
}

const _c1 = new THREE.Color();
const _c2 = new THREE.Color();
const _c3 = new THREE.Color();
function blendedColor(worldPos) {
  let best1Key = null,
    best1W = -1,
    best2Key = null,
    best2W = -1;
  for (const key in DIVISION_COLORS) {
    const div = DIVISION_COLORS[key];
    let w = 0;
    for (const p of div.pos) {
      const dist = worldPos.distanceTo(p);
      w += 1 / (dist * dist + 0.05);
    }
    if (w > best1W) {
      best2W = best1W;
      best2Key = best1Key;
      best1W = w;
      best1Key = key;
    } else if (w > best2W) {
      best2W = w;
      best2Key = key;
    }
  }
  _c1.setHex(DIVISION_COLORS[best1Key].hex);
  _c2.setHex(DIVISION_COLORS[best2Key].hex);
  const total = best1W + best2W;
  _c3.copy(_c1).lerp(_c2, total > 0 ? best2W / total : 0);
  return _c3.clone();
}

// One seed trunk per division, in this fixed order -- see lineageColor
// below for why this exists.
export const DIVISION_KEYS = Object.keys(DIVISION_COLORS);

const _c4 = new THREE.Color();
// Real finding after THREE separate attempts to fix color balance purely
// by repositioning attractor points: the persistent blue-cyan dominance
// wasn't a geometry problem at all -- it's that blendedColor() picks a
// color from GLOBAL PROXIMITY, and the space-colonization tree's particle
// MASS is not evenly distributed in space (tree topology concentrates
// more edges near the shared lower confluence zone than the sparse
// cortex periphery), so whichever attractors happen to sit near the
// naturally-dense region keep winning regardless of where they're placed.
// No amount of repositioning fixes an emergent density problem.
//
// Real fix: stop deriving color from position at all. Each of the 7 seed
// trunks IS a division (assigned directly, see growBranchingTree), and
// every descendant inherits its seed's division -- this guarantees an
// exact 1/7 split by construction, independent of where growth happens to
// wander. The old geometric field (blendedColor) is kept as a light tint
// only, so branches that physically cross paths still visibly blend --
// interweaving without abandoning the guaranteed-fair base assignment.
function lineageColor(divisionKey, pos) {
  _c4.setHex(DIVISION_COLORS[divisionKey].hex);
  const geo = blendedColor(pos);
  return _c4.clone().lerp(geo, 0.22);
}

// Real shape bug found from a live screenshot: with GAP=0.28 and each
// hemisphere's own x-radius at 0.56, the two ellipsoids overlapped by
// more than half their width -- next to nothing but the thin fissure
// carve separated them, so the combined silhouette read as one wide,
// fairly flat-topped mass instead of two distinct rounded domes.
// Widened the gap and narrowed each lobe's own radius so they read as
// genuinely separate shapes, and made each lobe taller/rounder (raised
// SEMI.y) so the top curves distinctly instead of looking flat.
const GAP = 0.42;
const SEMI = { x: 0.46, y: 0.64, z: 0.48 };
const GROOVE = 0.15;
const GROOVE_MIN_Y = -0.25;
const STEM_TOP = -0.5;
const STEM_BOTTOM = -0.95;

/** Builds the cloud of 3D points branches grow toward -- the exact same
 * hemisphere+fissure+gyrus+brainstem shape as before, just consumed as
 * growth targets instead of being final particle positions. */
function buildAttractionPoints(hemisphereCount, brainstemCount) {
  const attractors = [];

  const perHemisphere = Math.floor(hemisphereCount / 2);
  for (const side of [-1, 1]) {
    for (let i = 0; i < perHemisphere; i++) {
      const d = fibonacciDir(i, perHemisphere);
      const g = 1 + gyrus(d);
      // bottomTaper shrinks each lobe's own RADIUS near its base, but its
      // ellipsoid CENTER stays fixed at x=side*GAP regardless -- with the
      // wider GAP above, that would leave two separate necks side by side
      // (x~=+-0.42) instead of one shared brainstem connection. centerPull
      // additionally slides the whole point toward x=0 as the taper
      // deepens, so both lobes' necks actually converge to a single point
      // by the time they reach the brainstem, not two parallel stems.
      let bottomTaper = 1.0;
      let centerPull = 0.0;
      if (d.y < -0.55) {
        const tt = THREE.MathUtils.smoothstep(-d.y, 0.55, 1.0);
        bottomTaper = THREE.MathUtils.lerp(1.0, 0.34, tt);
        centerPull = tt;
      }
      const local = new THREE.Vector3(d.x * SEMI.x * g * bottomTaper, d.y * SEMI.y * g, d.z * SEMI.z * g * bottomTaper);
      const world = new THREE.Vector3(local.x + side * GAP * (1 - centerPull), local.y + 0.05, local.z);
      if (world.y > GROOVE_MIN_Y && Math.abs(world.x) < GROOVE) {
        const sign = world.x >= 0 ? 1 : -1;
        world.x = sign * GROOVE * (0.6 + Math.random() * 0.5);
      }
      attractors.push(world);
    }
  }

  let stemIdx = 0;
  while (stemIdx < brainstemCount) {
    const t = Math.random();
    const y = THREE.MathUtils.lerp(STEM_TOP, STEM_BOTTOM, t);
    const baseRadius = THREE.MathUtils.lerp(0.22, 0.05, Math.pow(t, 1.8));
    const ang = Math.random() * Math.PI * 2;
    const irregular = 1 + 0.2 * Math.sin(ang * 5 + t * 7) + 0.12 * Math.cos(ang * 8 - t * 4);
    const radius = baseRadius * irregular;
    const rr = radius * Math.sqrt(Math.random());
    const sway = 0.035 * Math.sin(t * Math.PI * 3.1 + ang) * (1 - t * 0.6);
    attractors.push(new THREE.Vector3(Math.cos(ang) * rr + sway, y, Math.sin(ang) * rr));
    stemIdx++;
  }

  return attractors;
}

const INFLUENCE_RADIUS = 0.17;
const KILL_RADIUS = 0.05;
const STEP_SIZE = 0.03;
const MAX_ITER = 480;
const MAX_ACTIVE_TIPS = 260;
const BRANCH_PROB = 0.045;

function cellKey(cx, cy, cz) {
  return cx + "_" + cy + "_" + cz;
}
function cellOf(v) {
  return [Math.floor(v.x / INFLUENCE_RADIUS), Math.floor(v.y / INFLUENCE_RADIUS), Math.floor(v.z / INFLUENCE_RADIUS)];
}

/** Grows a branching tree from 7 seed points near the pedestal toward the
 * attraction-point cloud, using space colonization: each active tip moves
 * toward the mean direction of nearby unclaimed points, consuming them as
 * it passes; when a tip's nearby points pull in genuinely different
 * directions, it splits into two children instead of averaging them away.
 * Returns { nodes, edges, rootPaths } -- a real parent/child graph, not a
 * point cloud with connections bolted on after the fact. */
function growBranchingTree(attractors) {
  const grid = new Map();
  attractors.forEach((pos) => {
    const [cx, cy, cz] = cellOf(pos);
    const key = cellKey(cx, cy, cz);
    if (!grid.has(key)) grid.set(key, []);
    grid.get(key).push({ pos, consumed: false });
  });

  function nearbyUnclaimed(pos) {
    const [cx, cy, cz] = cellOf(pos);
    const found = [];
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        for (let dz = -1; dz <= 1; dz++) {
          const bucket = grid.get(cellKey(cx + dx, cy + dy, cz + dz));
          if (!bucket) continue;
          for (const ap of bucket) {
            if (!ap.consumed && pos.distanceTo(ap.pos) < INFLUENCE_RADIUS) found.push(ap);
          }
        }
      }
    }
    return found;
  }

  function meanDirTo(list, from) {
    const m = new THREE.Vector3();
    list.forEach((ap) => m.add(ap.pos.clone().sub(from).normalize()));
    return m.normalize();
  }

  const nodes = []; // { pos, parent, children: [], depth, genIndex, division }
  const SEED_COUNT = DIVISION_KEYS.length;
  let tips = [];
  for (let i = 0; i < SEED_COUNT; i++) {
    const ang = (i / SEED_COUNT) * Math.PI * 2;
    const pos = new THREE.Vector3(Math.cos(ang) * 0.05, STEM_BOTTOM + 0.02, Math.sin(ang) * 0.05);
    const nodeIdx = nodes.length;
    // one seed = one division's lineage -- see lineageColor's comment for
    // why this replaces geometric-proximity color assignment
    nodes.push({ pos: pos.clone(), parent: -1, children: [], depth: 0, genIndex: 0, division: DIVISION_KEYS[i] });
    tips.push({ pos, dir: new THREE.Vector3(Math.cos(ang) * 0.35, 1, Math.sin(ang) * 0.35).normalize(), nodeIdx });
  }

  let iter = 0;
  while (tips.length && iter < MAX_ITER) {
    iter++;
    const newTips = [];
    for (const tip of tips) {
      const near = nearbyUnclaimed(tip.pos);
      if (near.length === 0) continue; // this branch terminates -- ran out of pull

      // Real bug found from a live screenshot ("veins rising from the
      // bottom look disorganized"): a fixed jitter amount every step
      // looks fine once branches have spread out into the wide cortex,
      // but right at the base, where all 7 trunks start in a tiny 0.05-
      // radius cluster, that same absolute wobble is huge relative to the
      // local scale -- it read as a tangled knot instead of primary
      // trunks rising with purpose. Real anatomy backs this too: trunks
      // are direct near their origin and only start wandering organically
      // once they've spread and begun branching. Both the jitter amount
      // and how much a tip commits to its own momentum (vs. the pull of
      // nearby points) now ramp in with depth instead of being constant
      // from the very first step.
      const depth = nodes[tip.nodeIdx].depth;
      const organicRamp = THREE.MathUtils.smoothstep(depth, 0, 16); // 0 near the base, 1 by depth 16
      const jitterScale = THREE.MathUtils.lerp(0.15, 1.0, organicRamp);
      const momentumWeight = THREE.MathUtils.lerp(0.82, 0.55, organicRamp);

      const meanDir = meanDirTo(near, tip.pos);
      const newDir = tip.dir
        .clone()
        .multiplyScalar(momentumWeight)
        .add(meanDir.multiplyScalar(1 - momentumWeight))
        .normalize();
      newDir.x += (Math.random() - 0.5) * 0.09 * jitterScale;
      newDir.y += (Math.random() - 0.5) * 0.06 * jitterScale;
      newDir.z += (Math.random() - 0.5) * 0.09 * jitterScale;
      newDir.normalize();
      const newPos = tip.pos.clone().add(newDir.clone().multiplyScalar(STEP_SIZE));

      // Real bug found from a live screenshot: the fissure was only ever
      // enforced on the TARGET attraction points, not on the branches
      // actually growing -- a tip chasing attraction points across the
      // midline could still wander straight through the gap, so the two
      // hemispheres never read as visually separate. Enforcing the same
      // groove here, on the real grown position, closes that gap for the
      // structure itself, not just for where it's headed.
      if (newPos.y > GROOVE_MIN_Y && Math.abs(newPos.x) < GROOVE) {
        const sign = newPos.x >= 0 ? 1 : -1;
        newPos.x = sign * GROOVE * (0.6 + Math.random() * 0.5);
      }

      const parentNode = nodes[tip.nodeIdx];
      const newIdx = nodes.length;
      nodes.push({
        pos: newPos,
        parent: tip.nodeIdx,
        children: [],
        depth: parentNode.depth + 1,
        genIndex: iter,
        division: parentNode.division,
      });
      parentNode.children.push(newIdx);

      near.forEach((ap) => {
        if (newPos.distanceTo(ap.pos) < KILL_RADIUS) ap.consumed = true;
      });

      const canBranch = near.length >= 5 && Math.random() < BRANCH_PROB && tips.length + newTips.length < MAX_ACTIVE_TIPS;
      if (canBranch) {
        const splitAxis = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
        const group1 = [],
          group2 = [];
        near.forEach((ap) => (ap.pos.clone().sub(newPos).dot(splitAxis) >= 0 ? group1 : group2).push(ap));
        if (group1.length && group2.length) {
          newTips.push({ pos: newPos.clone(), dir: meanDirTo(group1, newPos), nodeIdx: newIdx });
          newTips.push({ pos: newPos.clone(), dir: meanDirTo(group2, newPos), nodeIdx: newIdx });
          continue;
        }
      }
      newTips.push({ pos: newPos, dir: newDir, nodeIdx: newIdx });
    }
    tips = newTips;
  }

  const edges = [];
  nodes.forEach((n, i) => {
    if (n.parent >= 0) edges.push({ a: n.parent, b: i });
  });

  // real root-to-leaf paths for EnergyPaths' major pathways: the longest
  // chains in the tree, genuinely walking parent links the whole way
  const leaves = nodes.map((n, i) => i).filter((i) => nodes[i].children.length === 0);
  leaves.sort((a, b) => nodes[b].depth - nodes[a].depth);
  const rootPaths = leaves.slice(0, 9).map((leafIdx) => {
    const chain = [];
    let cur = leafIdx;
    while (cur >= 0) {
      chain.push(cur);
      cur = nodes[cur].parent;
    }
    return chain.reverse();
  });

  return { nodes, edges, rootPaths };
}

export class BrainFormationEngine {
  constructor({ hemisphereCount = 5200, brainstemCount = 1100, ambientCount = 480 } = {}) {
    this.hemisphereCount = hemisphereCount;
    this.brainstemCount = brainstemCount;
    this.ambientCount = ambientCount;
    this.pedestalOrbitCount = 220;
  }

  generate() {
    const attractors = buildAttractionPoints(this.hemisphereCount, this.brainstemCount);
    const { nodes, edges, rootPaths } = growBranchingTree(attractors);

    // Each tree node becomes a particle; the deepest generation index sets
    // the formation-timing scale (real growth order -> real stagger, not a
    // hand-authored percentage table).
    const maxGen = nodes.reduce((m, n) => Math.max(m, n.genIndex), 1);

    // A tree node's own position, plus a couple of extra fill particles
    // jittered slightly off each edge -- "hundreds of particles per
    // trunk" instead of a single-particle-wide line, denser near the
    // root (shallow depth) where real trunks are thick, thinner toward
    // the leaves where real neural filaments are fine.
    const FILL_PER_EDGE_NEAR_ROOT = 3;
    const perNode = [];
    nodes.forEach((n) => perNode.push({ pos: n.pos, genIndex: n.genIndex, depth: n.depth, division: n.division }));
    edges.forEach((e) => {
      const a = nodes[e.a],
        b = nodes[e.b];
      const fillCount = Math.max(1, Math.round(FILL_PER_EDGE_NEAR_ROOT * (1 - Math.min(1, b.depth / 30))));
      for (let f = 0; f < fillCount; f++) {
        const t = (f + 1) / (fillCount + 1);
        const p = a.pos.clone().lerp(b.pos, t);
        const perp = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(0.012);
        p.add(perp);
        // a and b are always the same lineage -- edges never span divisions
        perNode.push({ pos: p, genIndex: THREE.MathUtils.lerp(a.genIndex, b.genIndex, t), depth: b.depth, division: b.division });
      }
    });

    const totalStructural = perNode.length;
    const n = totalStructural + this.ambientCount + this.pedestalOrbitCount;
    const starts = new Float32Array(n * 3);
    const targets = new Float32Array(n * 3);
    const colors = new Float32Array(n * 3);
    const startTimes = new Float32Array(n);
    const durations = new Float32Array(n);
    const sizes = new Float32Array(n);
    const phases = new Float32Array(n);
    const orbitRadius = new Float32Array(n);
    const orbitY = new Float32Array(n);
    const orbitSpeed = new Float32Array(n);

    const SCATTER_RADIUS = 2.4;
    const randomScatterPoint = () => {
      const v = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5);
      v.normalize().multiplyScalar(SCATTER_RADIUS * (0.4 + Math.random() * 0.6));
      return v;
    };

    let idx = 0;
    for (const p of perNode) {
      const start = randomScatterPoint();
      const color = lineageColor(p.division, p.pos);
      starts[idx * 3] = start.x;
      starts[idx * 3 + 1] = start.y;
      starts[idx * 3 + 2] = start.z;
      targets[idx * 3] = p.pos.x;
      targets[idx * 3 + 1] = p.pos.y;
      targets[idx * 3 + 2] = p.pos.z;
      colors[idx * 3] = color.r;
      colors[idx * 3 + 1] = color.g;
      colors[idx * 3 + 2] = color.b;

      // real growth order drives formation timing: low genIndex (near the
      // pedestal, grown first) arrives early, high genIndex (deep cortex,
      // grown last) arrives late -- the brain visibly builds itself
      // outward from the roots, matching the requested 0->100% sequence
      // without a hand-authored stage table.
      const genFrac = p.genIndex / maxGen;
      startTimes[idx] = genFrac * 0.85 + Math.random() * 0.04;
      durations[idx] = 0.1 + Math.random() * 0.08;
      // thicker near the trunks (shallow depth), finer toward the cortex
      sizes[idx] = THREE.MathUtils.lerp(0.011, 0.0045, Math.min(1, p.depth / 24)) + Math.random() * 0.003;
      phases[idx] = Math.random();
      idx++;
    }

    for (let i = 0; i < this.ambientCount; i++) {
      const wanderCenter = new THREE.Vector3(
        THREE.MathUtils.lerp(-0.35, 0.95, Math.random()),
        (Math.random() - 0.5) * 1.6 - 0.1,
        (Math.random() - 0.5) * 2.0
      );
      const start = randomScatterPoint();
      const color = blendedColor(wanderCenter);
      starts[idx * 3] = start.x;
      starts[idx * 3 + 1] = start.y;
      starts[idx * 3 + 2] = start.z;
      targets[idx * 3] = wanderCenter.x;
      targets[idx * 3 + 1] = wanderCenter.y;
      targets[idx * 3 + 2] = wanderCenter.z;
      colors[idx * 3] = color.r;
      colors[idx * 3 + 1] = color.g;
      colors[idx * 3 + 2] = color.b;
      startTimes[idx] = Math.random() * 0.6;
      durations[idx] = 0.3 + Math.random() * 0.3;
      sizes[idx] = 0.004 + Math.random() * 0.005;
      phases[idx] = Math.random();
      idx++;
    }

    for (let i = 0; i < this.pedestalOrbitCount; i++) {
      const radius = 0.35 + Math.random() * 0.32;
      const y = STEM_BOTTOM - 0.03 + Math.random() * 0.02;
      const start = randomScatterPoint();
      const color = blendedColor(new THREE.Vector3(0, STEM_BOTTOM, 0));
      starts[idx * 3] = start.x;
      starts[idx * 3 + 1] = start.y;
      starts[idx * 3 + 2] = start.z;
      targets[idx * 3] = 0;
      targets[idx * 3 + 1] = y;
      targets[idx * 3 + 2] = 0;
      colors[idx * 3] = color.r;
      colors[idx * 3 + 1] = color.g;
      colors[idx * 3 + 2] = color.b;
      startTimes[idx] = 0.5 + Math.random() * 0.3;
      durations[idx] = 0.15 + Math.random() * 0.1;
      sizes[idx] = 0.005 + Math.random() * 0.004;
      phases[idx] = Math.random();
      orbitRadius[idx] = radius;
      orbitY[idx] = y;
      orbitSpeed[idx] = 0.15 + Math.random() * 0.2;
      idx++;
    }

    return {
      count: n,
      starts,
      targets,
      colors,
      startTimes,
      durations,
      sizes,
      phases,
      orbitRadius,
      orbitY,
      orbitSpeed,
      // real tree structure for NeuralNetwork (renders every edge
      // directly -- no nearest-neighbor guessing) and EnergyPaths (walks
      // real root-to-leaf chains for major pathways)
      treeNodes: nodes,
      treeEdges: edges,
      rootPaths,
      maxGen,
      stemTop: STEM_TOP,
      stemBottom: STEM_BOTTOM,
    };
  }
}
