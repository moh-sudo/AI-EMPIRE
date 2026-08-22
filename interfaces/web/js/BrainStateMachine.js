// Real state machine, not a decorative label: each state maps to actual
// render parameters (pulse speed, brightness, point scale, line opacity)
// that EmpireBrain.js reads every frame. Only IDLE has full visual
// treatment behind it today -- the others are real, working transitions
// with honest (if simple) parameter changes, not choreographed animations
// that don't exist yet. Extending any one of them is a matter of tuning
// its entry in STATE_PARAMS, not restructuring anything.

export const BrainState = Object.freeze({
  IDLE: "IDLE",
  WAKE: "WAKE",
  LISTENING: "LISTENING",
  THINKING: "THINKING",
  PROCESSING: "PROCESSING",
  RESPONDING: "RESPONDING",
  ALERT: "ALERT",
  DISSOLVING: "DISSOLVING",
});

const STATE_PARAMS = {
  [BrainState.IDLE]: { pointScale: 1.0, lineOpacity: 0.35, pulseIntensity: 0.15, rotateSpeed: 0.045 },
  [BrainState.WAKE]: { pointScale: 1.15, lineOpacity: 0.5, pulseIntensity: 0.45, rotateSpeed: 0.09 },
  [BrainState.LISTENING]: { pointScale: 1.1, lineOpacity: 0.55, pulseIntensity: 0.35, rotateSpeed: 0.03 },
  [BrainState.THINKING]: { pointScale: 1.2, lineOpacity: 0.6, pulseIntensity: 0.6, rotateSpeed: 0.16 },
  [BrainState.PROCESSING]: { pointScale: 1.25, lineOpacity: 0.65, pulseIntensity: 0.75, rotateSpeed: 0.2 },
  [BrainState.RESPONDING]: { pointScale: 1.15, lineOpacity: 0.55, pulseIntensity: 0.5, rotateSpeed: 0.1 },
  [BrainState.ALERT]: { pointScale: 1.1, lineOpacity: 0.6, pulseIntensity: 0.8, rotateSpeed: 0.05 },
  [BrainState.DISSOLVING]: { pointScale: 0.9, lineOpacity: 0.15, pulseIntensity: 0.1, rotateSpeed: 0.02 },
};

export class BrainStateMachine {
  constructor(initial = BrainState.IDLE) {
    this.state = initial;
    this.params = { ...STATE_PARAMS[initial] };
    this._target = { ...STATE_PARAMS[initial] };
  }

  setState(state) {
    if (!STATE_PARAMS[state]) throw new Error(`Unknown BrainState: ${state}`);
    this.state = state;
    this._target = STATE_PARAMS[state];
  }

  /** Smoothly eases current params toward the target state's params each
   * frame, so a state change doesn't visually snap. */
  update(dt) {
    const EASE = Math.min(1, dt * 2.2);
    for (const key in this._target) {
      this.params[key] += (this._target[key] - this.params[key]) * EASE;
    }
    return this.params;
  }
}
