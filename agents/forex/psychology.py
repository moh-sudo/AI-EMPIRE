"""Psychology Coaching Agent v0.1 -- Forex Division.

Per the real design (governance doc section 3.1): Trading Psychology
is Stage 3 (30% weight) of the gate, and explicitly "Runs BEFORE
execution" -- its job is a Discipline Report, Emotional Alerts, and
Rule Violations, checked before Entry & Exit is ever allowed to act.

Grounded in what Mohamed already identified about himself in his
handwritten trading journal, not generic trading psychology advice:
- Named struggles: entry timing, "trusting the process", intrusive
  thoughts before/during trades, panic.
- Named concentration killers: phone, gossip/"stories", thinking about
  unrelated things (admiring others' lives), friends, family stories.
- Named discipline rules: avoid fear/overconfidence/panic/stressing,
  never revenge-trade (close the loss and look for the mistake
  instead), journal instead of talking to others about progress.
- Sleep target: asleep by 9:30 PM, awake by 3:30 AM (to catch
  Asian/London overlap).
"""

from dataclasses import dataclass, field
from typing import Optional

KNOWN_DISTRACTIONS = ["phone", "gossip", "stories", "admiring", "friends", "family"]
REVENGE_TRADE_SIGNALS = [
    "make it back", "get it back", "double down", "chase", "revenge",
    "angry", "furious", "need to win this one", "prove", "immediately",
]
TARGET_SLEEP_TIME = "21:30"
TARGET_WAKE_TIME = "03:30"

SEVERITY_OK = "ok"
SEVERITY_CAUTION = "caution"
SEVERITY_PAUSE = "pause"

# The 10-principle psychology reference Mohamed provided directly
# (2026-07-24), distinct from what his handwritten journal captured --
# this is general trading-psychology discipline, not his personal
# self-diagnosed patterns. Published to memory_knowledge, not
# hardcoded into the check functions, so it stays a reference other
# agents (and Mohamed) can query rather than silently-applied rules.
PSYCHOLOGY_REFERENCE_TEXT = """Forex trading psychology principles (core discipline framework):
1. Patience -- wait for the complete setup, don't force a trade out of boredom or impatience.
2. Discipline -- follow the trading plan exactly; don't skip steps (e.g. liquidity sweep, CHoCH, order block entry).
3. Emotional Control -- never trade from excitement, anger, frustration, FOMO, or a need to recover losses.
4. Accept losses are normal -- a loss doesn't mean the analysis or the strategy was wrong; judge by whether the rules were followed, not the outcome.
5. Risk Management -- know the stop-loss, the exact loss if it's hit, and whether that loss is acceptable, before entering.
6. Avoid revenge trading -- after a loss, ask "would I take this trade if the previous one had won?" If no, don't take it.
7. Don't chase the market -- wait for a pullback into the planned area rather than entering on a move that's already run.
8. Confidence comes from testing -- backtesting, reviewing past trades, and journaling build real confidence, not hope.
9. Think in probabilities -- no single setup is guaranteed; the edge shows up over many trades, not one.
10. Stay consistent -- don't switch strategies after every loss; constant switching means never learning whether any one approach has a real edge."""

# The 7-item pre-trade mental checklist, exactly as given. Each key
# maps to a yes/no self-report just before entering a trade -- this is
# a per-trade gate, distinct from pre_session_checkin() which runs
# once at the start of a session.
PRE_TRADE_CHECKLIST_ITEMS: dict[str, str] = {
    "valid_setup": "Is this a valid setup according to my rules?",
    "htf_bias_aligned": "Am I trading with the higher-timeframe bias?",
    "calm_not_emotional": "Am I calm and not acting on emotion?",
    "know_sl_tp": "Do I know exactly where my stop-loss and take-profit are?",
    "risk_acceptable": "Is the risk acceptable?",
    "outcome_independent": "Would I still take this trade if the previous one had won or lost?",
    "following_plan": "Am I following my plan rather than reacting to the market?",
}

# Failing either of these two alone is enough to pause -- they're the
# most direct gateways to emotionally-driven losses (mirrors the
# revenge-trade detection in post_loss_checkin()).
_CRITICAL_CHECKLIST_ITEMS = {"calm_not_emotional", "outcome_independent"}


@dataclass
class DisciplineReport:
    kind: str  # "pre_session" | "post_loss"
    severity: str  # ok | caution | pause
    flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def pre_session_checkin(
    *,
    slept_on_time: Optional[bool] = None,
    distractions_today: Optional[str] = None,
    emotional_state: Optional[str] = None,
) -> DisciplineReport:
    """Runs before a trading session. Mirrors the journal's own rules:
    sleep schedule, the specific named distractions, and the four
    things to avoid (fear, overconfidence, panic, stressing)."""
    flags: list[str] = []
    notes: list[str] = []

    if slept_on_time is False:
        flags.append("sleep_off_schedule")
        notes.append(f"Sleep wasn't on schedule (target: asleep by {TARGET_SLEEP_TIME}, awake by {TARGET_WAKE_TIME}) -- this directly affects session quality per your own journal.")

    if distractions_today:
        hit = [d for d in KNOWN_DISTRACTIONS if d in distractions_today.lower()]
        if hit:
            flags.append("known_distraction_present")
            notes.append(f"Named distraction(s) present today: {', '.join(hit)} -- these are the exact things you identified as concentration killers.")

    if emotional_state:
        state_lower = emotional_state.lower()
        for bad_state in ("fear", "greed", "overconfiden", "panic", "stress"):
            if bad_state in state_lower:
                flags.append(f"emotional_state_{bad_state.rstrip('en')}")
                notes.append(f"Emotional state includes '{bad_state}' -- one of the four things you named to avoid before trading.")

    if len(flags) >= 2:
        severity = SEVERITY_PAUSE
        notes.append("Multiple flags present -- consider sitting this session out rather than forcing a trade.")
    elif flags:
        severity = SEVERITY_CAUTION
    else:
        severity = SEVERITY_OK

    return DisciplineReport(kind="pre_session", severity=severity, flags=flags, notes=notes)


def post_loss_checkin(reflection: str) -> DisciplineReport:
    """Runs after a loss, before any next trade. Looks for revenge-
    trading language -- your own rule is to close and look for the
    mistake, never chase the loss back."""
    flags: list[str] = []
    notes: list[str] = []

    reflection_lower = reflection.lower()
    hit = [s for s in REVENGE_TRADE_SIGNALS if s in reflection_lower]
    if hit:
        flags.append("revenge_trade_risk")
        notes.append(f"Language suggesting revenge-trading risk detected ({', '.join(hit)}) -- your own rule: close and look for the mistake, don't chase it back.")

    severity = SEVERITY_PAUSE if flags else SEVERITY_OK
    if not flags:
        notes.append("No revenge-trading signals detected in this reflection.")

    return DisciplineReport(kind="post_loss", severity=severity, flags=flags, notes=notes)


def pre_trade_checklist(answers: dict[str, bool]) -> DisciplineReport:
    """Per-trade gate, run right before entering -- not once per
    session like pre_session_checkin(), but every single time. Missing
    keys are treated as unanswered/failed, never assumed true."""
    flags: list[str] = []
    notes: list[str] = []
    critical_failed = False

    for key, question in PRE_TRADE_CHECKLIST_ITEMS.items():
        answered_yes = bool(answers.get(key, False))
        if not answered_yes:
            flags.append(key)
            notes.append(f"'{question}' -- not confirmed.")
            if key in _CRITICAL_CHECKLIST_ITEMS:
                critical_failed = True

    if critical_failed or len(flags) >= 2:
        severity = SEVERITY_PAUSE
    elif flags:
        severity = SEVERITY_CAUTION
    else:
        severity = SEVERITY_OK
        notes.append("All 7 checklist items confirmed -- best chance of executing the plan consistently.")

    return DisciplineReport(kind="pre_trade", severity=severity, flags=flags, notes=notes)


def run_psychology_reference_publish() -> dict:
    """Live entry point: publishes the 10-principle psychology
    reference to memory_knowledge (division=forex) so other agents can
    query it, same pattern as Strategy's reference publish."""
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-psychology-v0.1",
        content=PSYCHOLOGY_REFERENCE_TEXT,
        source="mohamed-provided-2026-07-24",
        metadata={"checklist_items": list(PRE_TRADE_CHECKLIST_ITEMS.keys())},
    )


# ─────────────────────────────────────────────────────────────────
# 2026-07-25: personal mindset notes from Mohamed's transcribed
# handwritten notebook (page 39-40), distinct source from both the
# journal ("JOURNEY OF MY FOREX TRADING.docx") and the 10-principle
# generic reference above. Kept as its own memory_knowledge entry
# rather than merged into either, same reasoning as Strategy's
# journal/SMC/ICT/toolkit split. Fixed a real gap while adding this:
# these notes explicitly say "No fear, No Greed, and No over
# confidence" but pre_session_checkin()'s bad-state list only had
# fear/overconfident/panic/stress -- "greed" was missing entirely
# despite being one of his own three named things to avoid. Added
# above.
# ─────────────────────────────────────────────────────────────────

PERSONAL_MINDSET_REFERENCE_TEXT = """Personal trading mindset (Mohamed's own notes, page 39-40):
Before trading: sit down, calm the mind, focus on the trading journey. Come with a clear mind.
Stop thinking of money and a luxury lifestyle -- focus on goals and achievements instead. Have a
plan to execute the trade. Don't let ego take you into a bad step. Set a small daily target so
you can adapt, rather than an unrealistic one. No fear, no greed, no over-confidence. Moral
discipline is what makes someone successful in life. Never give up on trading, even when it's
hard. Patience is everything in trading. Everyday learning is learning -- writing (journaling) is
a main part of success. Stay away from behavior that could undermine success more broadly, not
just trading-specific mistakes."""


def run_personal_mindset_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-psychology-v0.1",
        content=PERSONAL_MINDSET_REFERENCE_TEXT,
        source="mohamed-forex-notebook-2026-07-25",
        metadata={"topic": "personal_mindset"},
    )


def log_checkin(report: DisciplineReport, raw_input: str, account: Optional[str] = None) -> dict:
    """Writes the discipline report to memory_experience so it's part
    of the same searchable history as trades and journal entries.
    account is optional (a pre-session check-in might not be tied to
    one specific account) but should be supplied whenever a check-in
    is genuinely account-specific, so Performance Review can tie
    discipline history to a given account's readiness."""
    from agents.forex._memory_helpers import safe_add_experience

    return safe_add_experience(
        division="forex",
        agent_id="forex-psychology-v0.1",
        event_type=f"psychology_{report.kind}",
        context=raw_input,
        outcome=report.severity,
        metadata={"flags": report.flags, "notes": report.notes, "account": account},
    )
