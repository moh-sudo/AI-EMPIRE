"""Risk Management Agent v0.1 -- Forex Division.

Per Mohamed's explicit design note: this should be a two-way
*discussion*, not silent enforcement (Law 4: AI advises, humans
decide) -- evaluate_*_risk() is meant to be run a proposed risk %
past before entering a trade, not a gate that silently blocks.

Three account profiles, handled differently because their actual rules
are different:
  - FundedNext Stellar Lite ($10,000): real, externally-imposed prop
    firm rules -- breaching the fixed 4% daily loss limit or the fixed
    8% static drawdown loses the funded account entirely. Pulled
    directly from fundednext.com/general-rules/cfds/trading-objectives
    (2026-07-24) -- see PENDING items in CONTEXT.md for the source.
  - Exness / IC Markets: personal live accounts, no external rule set.
    Mohamed hasn't deposited yet ("depends on my pocket, not sure yet,
    have not invested yet") -- so these take an explicit balance every
    call rather than a stored account size. Purely advisory, grounded
    in the 0.5-1% per trade guidance already published in the SMC/ICT
    strategy references.
"""

from dataclasses import dataclass, field
from typing import Literal

FUNDEDNEXT_STELLAR_LITE_10K = {
    "initial_balance": 10_000.0,
    "daily_loss_limit_pct": 4.0,  # FundedNext's actual published rule -- $400
    "personal_daily_loss_limit_dollars": 250.0,  # Mohamed's own tighter self-imposed line, used as the operative check
    "max_drawdown_pct": 8.0,  # static -- fixed floor set at account start, never trails
    "drawdown_type": "static",
    "phase1_target_pct": 8.0,
    "phase2_target_pct": 4.0,
    "min_trading_days": 5,
}

# From the SMC/ICT strategy references already published:
# "risk only 0.5-1% of your account per trade."
PERSONAL_ACCOUNT_RECOMMENDED_RISK_PCT = (0.5, 1.0)

VERDICT_REASONABLE = "reasonable"
VERDICT_CAUTION = "caution"
VERDICT_BREACH = "would_breach_limit"


@dataclass
class RiskEvaluation:
    account: str
    proposed_risk_pct: float
    proposed_risk_dollars: float
    verdict: str
    notes: list[str] = field(default_factory=list)


def evaluate_fundednext_risk(
    proposed_risk_pct: float,
    current_balance: float,
    todays_pnl: float = 0.0,
) -> RiskEvaluation:
    """current_balance is today's actual balance (not the fixed
    $10,000 initial) -- the daily-loss check resets each day, but the
    drawdown floor is static and set from the initial balance,
    regardless of how the account has grown or shrunk since."""
    account = FUNDEDNEXT_STELLAR_LITE_10K
    initial = account["initial_balance"]
    proposed_dollars = current_balance * (proposed_risk_pct / 100)

    firm_daily_loss_limit_dollars = initial * (account["daily_loss_limit_pct"] / 100)
    personal_daily_loss_limit_dollars = account["personal_daily_loss_limit_dollars"]
    daily_loss_remaining = personal_daily_loss_limit_dollars - max(0.0, -todays_pnl)

    drawdown_floor = initial * (1 - account["max_drawdown_pct"] / 100)
    drawdown_buffer = current_balance - drawdown_floor

    notes: list[str] = []
    verdict = VERDICT_REASONABLE

    if proposed_dollars > daily_loss_remaining:
        verdict = VERDICT_BREACH
        notes.append(
            f"Risking ${proposed_dollars:,.2f} would exceed today's remaining daily-loss "
            f"buffer against your own ${personal_daily_loss_limit_dollars:,.2f} personal limit "
            f"(${daily_loss_remaining:,.2f} remaining) -- tighter than FundedNext's actual "
            f"${firm_daily_loss_limit_dollars:,.2f} rule, which you haven't hit yet."
        )
    elif proposed_dollars > daily_loss_remaining * 0.5:
        verdict = VERDICT_CAUTION
        notes.append(
            f"Risking ${proposed_dollars:,.2f} uses more than half of today's remaining "
            f"daily-loss buffer against your ${personal_daily_loss_limit_dollars:,.2f} personal "
            f"limit (${daily_loss_remaining:,.2f} remaining)."
        )

    if proposed_dollars > drawdown_buffer:
        verdict = VERDICT_BREACH
        notes.append(
            f"Risking ${proposed_dollars:,.2f} would exceed the remaining static drawdown "
            f"buffer (${drawdown_buffer:,.2f}) -- breaching this loses the funded account."
        )

    if verdict == VERDICT_REASONABLE:
        notes.append(f"${proposed_dollars:,.2f} ({proposed_risk_pct}%) is within both the daily-loss and drawdown buffers.")

    return RiskEvaluation(
        account="fundednext_stellar_lite_10k", proposed_risk_pct=proposed_risk_pct,
        proposed_risk_dollars=proposed_dollars, verdict=verdict, notes=notes,
    )


def evaluate_personal_account_risk(
    account: Literal["exness", "ic_markets"],
    proposed_risk_pct: float,
    balance: float,
) -> RiskEvaluation:
    """No externally-imposed rules -- purely advisory. balance must be
    supplied every call since there's no deposit yet to store a fixed
    size for."""
    proposed_dollars = balance * (proposed_risk_pct / 100)
    min_pct, max_pct = PERSONAL_ACCOUNT_RECOMMENDED_RISK_PCT

    if proposed_risk_pct > max_pct:
        verdict = VERDICT_CAUTION
        note = (
            f"{proposed_risk_pct}% is above the commonly recommended {min_pct}-{max_pct}% per "
            f"trade -- no external rule breaks here, but this is more aggressive than the "
            f"strategy references suggest."
        )
    else:
        verdict = VERDICT_REASONABLE
        note = f"{proposed_risk_pct}% is within the {min_pct}-{max_pct}% guidance from the strategy references."

    return RiskEvaluation(
        account=account, proposed_risk_pct=proposed_risk_pct,
        proposed_risk_dollars=proposed_dollars, verdict=verdict, notes=[note],
    )


# ─────────────────────────────────────────────────────────────────
# 2026-07-25: Mohamed's own personal daily/weekly/monthly/yearly target
# ladder, from his transcribed handwritten notebook (page 16-17, 42).
# Distinct from FundedNext's phase targets above (which are the prop
# firm's account-growth targets) -- this is a personal profit-taking
# discipline: a daily profit CAP, symmetric to the daily loss limit
# already enforced above, since his own notes are explicit ("not more
# than 300 or less than that"). The $10k/8%/$800 challenge-account math
# in his notes matches FUNDEDNEXT_STELLAR_LITE_10K's phase1_target_pct
# (8.0) exactly -- confirms the existing model, no numbers to add there.
# ─────────────────────────────────────────────────────────────────

DAILY_PROFIT_TARGET_DOLLARS = 300.0  # Mohamed's own cap -- stop for the day once hit, don't chase more
WEEKLY_PROFIT_TARGET_DOLLARS = 1_500.0  # 300 x 5 trading days
MONTHLY_PROFIT_TARGET_DOLLARS = 6_000.0
YEARLY_PROFIT_TARGET_DOLLARS = 72_000.0  # 6,000 x 12

DAILY_TARGET_REFERENCE_TEXT = """Personal profit-target ladder (Mohamed's own notes, page 16-17, 42):
Daily target: $300 -- explicitly "not more than 300 or less than that," i.e. a genuine stop-
trading-for-the-day cap once hit, not just a loose goal. Reward:risk should not exceed 3:1
(matches the Strategy Agent's own MOHAMED_MIN_REWARD_TO_RISK). Ladder: Weekly $1,500 (300 x 5
trading days) -> Monthly $6,000 -> Yearly $72,000 (6,000 x 12). Explicitly framed as a
consistency/discipline target, not a get-rich-quick number -- "struggle is the name of the game,
don't give up easily since you invested your time, strength and focus."
Challenge-account math (matches FundedNext Stellar Lite $10,000 already modeled here): 8% of
$10,000 = $800 target. Risk per trade: 0.5% = $50 loss if stopped out, 1% = $100 loss if stopped
out. Common reward:risk ratios named: 1:2 ($100 risk -> $200 gain), 1:3 ($100 -> $300), 1:5
($100 -> $500)."""


def run_daily_target_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-risk-management-v0.1",
        content=DAILY_TARGET_REFERENCE_TEXT,
        source="mohamed-forex-notebook-2026-07-25",
        metadata={
            "daily_target": DAILY_PROFIT_TARGET_DOLLARS,
            "weekly_target": WEEKLY_PROFIT_TARGET_DOLLARS,
            "monthly_target": MONTHLY_PROFIT_TARGET_DOLLARS,
            "yearly_target": YEARLY_PROFIT_TARGET_DOLLARS,
        },
    )


def check_daily_target_status(todays_pnl: float, target: float = DAILY_PROFIT_TARGET_DOLLARS) -> dict:
    """Profit-side counterpart to the daily-loss check in
    evaluate_fundednext_risk() -- Mohamed's own rule is a real stop-
    trading cap once the daily target is hit, not just a soft goal, so
    this reports a status rather than silently allowing more trades."""
    if todays_pnl >= target:
        return {"status": "target_hit", "notes": [f"Today's P&L (${todays_pnl:,.2f}) has reached or passed the ${target:,.2f} daily target -- your own rule is to stop for the day, not chase more."]}
    if todays_pnl >= target * 0.5:
        return {"status": "approaching_target", "notes": [f"Today's P&L (${todays_pnl:,.2f}) is over half of the ${target:,.2f} daily target."]}
    return {"status": "in_progress", "notes": [f"Today's P&L (${todays_pnl:,.2f}) is below the ${target:,.2f} daily target."]}


def log_risk_discussion(evaluation: RiskEvaluation) -> dict:
    from agents.forex._memory_helpers import safe_add_experience

    return safe_add_experience(
        division="forex",
        agent_id="forex-risk-management-v0.1",
        event_type="risk_discussion",
        context=f"Proposed {evaluation.proposed_risk_pct}% (${evaluation.proposed_risk_dollars:,.2f}) risk on {evaluation.account}.",
        outcome=evaluation.verdict,
        metadata={
            "account": evaluation.account, "proposed_risk_pct": evaluation.proposed_risk_pct,
            "proposed_risk_dollars": evaluation.proposed_risk_dollars, "notes": evaluation.notes,
        },
    )
