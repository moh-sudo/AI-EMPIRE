"""Performance Review Agent v0.1 -- Forex Division.

Per Mohamed's explicit design intent (2026-07-25): not just a P&L
summary -- this is the signal that decides whether an account has
actually earned trust for real money, built from real accumulated
history (Journaling's account-tagged trades + Psychology's account-
tagged check-ins), not just "the code runs without erroring." Entry &
Exit stays demo-only until this agent shows a genuine track record.

Computes the same kind of edge statistics as Backtesting Agent (win
rate, profit factor, expectancy) but applied to an account's REAL
trades -- kept as independent logic rather than a shared import, since
a backtest answers "does the rule set work in theory" and this answers
"is this account's actual trading working in practice," different
enough questions to keep the two agents' reasoning separately readable.

Never silently approves an account as ready -- assess_readiness()
fails closed (defaults to not-ready) the same way News Filter does
when it can't verify something, and always explains its reasoning.
"""

from dataclasses import dataclass, field

# General statistical heuristic, same one Backtesting uses -- not a
# number Mohamed specified.
MIN_TRADES_FOR_READINESS = 30

# More than 1 in 5 psychology check-ins hitting "pause" suggests the
# discipline layer isn't holding consistently yet.
MAX_ACCEPTABLE_PSYCHOLOGY_PAUSE_RATE_PCT = 20.0


@dataclass
class AccountEdgeStats:
    total_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate_pct: float
    profit_factor: float | None
    total_pnl: float
    expectancy: float | None


@dataclass
class PsychologyComplianceStats:
    total_checkins: int
    ok_count: int
    caution_count: int
    pause_count: int
    pause_rate_pct: float


@dataclass
class ReadinessAssessment:
    account: str
    ready: bool
    edge_stats: AccountEdgeStats
    psychology_stats: PsychologyComplianceStats
    reasons: list[str] = field(default_factory=list)


def fetch_account_trades(account: str) -> list[dict]:
    from shared.db import get_client

    c = get_client()
    r = (
        c.table("memory_experience")
        .select("id,metadata,outcome,created_at")
        .eq("division", "forex")
        .eq("event_type", "trade_closed")
        .filter("metadata->>account", "eq", account)
        .execute()
    )
    return r.data


def fetch_account_psychology_checkins(account: str) -> list[dict]:
    from shared.db import get_client

    c = get_client()
    r = (
        c.table("memory_experience")
        .select("id,event_type,outcome,metadata,created_at")
        .eq("division", "forex")
        .like("event_type", "psychology_%")
        .filter("metadata->>account", "eq", account)
        .execute()
    )
    return r.data


def compute_edge_stats(trades: list[dict]) -> AccountEdgeStats:
    """Pure logic over already-fetched trade rows (each shaped like a
    memory_experience row with a metadata dict) -- fully testable
    without the DB using synthetic rows."""
    if not trades:
        return AccountEdgeStats(0, 0, 0, 0, 0.0, None, 0.0, None)

    results = [t["metadata"].get("result") for t in trades]
    pnls = [float(t["metadata"].get("pnl", 0.0)) for t in trades]

    wins = results.count("win")
    losses = results.count("loss")
    breakevens = results.count("be")
    total = len(trades)
    win_rate = (wins / total) * 100 if total else 0.0

    gross_win = sum(p for p, res in zip(pnls, results, strict=True) if res == "win")
    gross_loss = abs(sum(p for p, res in zip(pnls, results, strict=True) if res == "loss"))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else None

    total_pnl = sum(pnls)
    expectancy = total_pnl / total if total else None

    return AccountEdgeStats(
        total_trades=total,
        wins=wins,
        losses=losses,
        breakevens=breakevens,
        win_rate_pct=round(win_rate, 2),
        profit_factor=round(profit_factor, 2) if profit_factor is not None else None,
        total_pnl=round(total_pnl, 2),
        expectancy=round(expectancy, 2) if expectancy is not None else None,
    )


def compute_psychology_compliance(checkins: list[dict]) -> PsychologyComplianceStats:
    """Pure logic, fully testable without the DB."""
    if not checkins:
        return PsychologyComplianceStats(0, 0, 0, 0, 0.0)

    outcomes = [c.get("outcome") for c in checkins]
    total = len(checkins)
    ok = outcomes.count("ok")
    caution = outcomes.count("caution")
    pause = outcomes.count("pause")
    pause_rate = (pause / total) * 100 if total else 0.0

    return PsychologyComplianceStats(
        total_checkins=total,
        ok_count=ok,
        caution_count=caution,
        pause_count=pause,
        pause_rate_pct=round(pause_rate, 2),
    )


def assess_readiness(
    account: str,
    edge_stats: AccountEdgeStats,
    psychology_stats: PsychologyComplianceStats,
    min_trades: int = MIN_TRADES_FOR_READINESS,
) -> ReadinessAssessment:
    """The actual "is this account ready for real money" judgment --
    combines sample size, profitability, and discipline compliance.
    Fails closed: any unmet condition means not-ready, and every
    verdict comes with the specific reasons, never a bare yes/no."""
    reasons: list[str] = []
    ready = True

    if edge_stats.total_trades < min_trades:
        ready = False
        reasons.append(
            f"Only {edge_stats.total_trades} logged trades -- need at least {min_trades} for a reliable sample."
        )

    if edge_stats.profit_factor is None or edge_stats.profit_factor <= 1.0:
        ready = False
        pf_display = (
            edge_stats.profit_factor if edge_stats.profit_factor is not None else "undefined (no losses or no wins yet)"
        )
        reasons.append(
            f"Profit factor is {pf_display} -- needs to be reliably above 1.0 before this counts as a working edge."
        )

    if psychology_stats.total_checkins == 0:
        ready = False
        reasons.append(
            "No psychology check-ins logged yet -- discipline compliance can't be assessed without any history."
        )
    elif psychology_stats.pause_rate_pct > MAX_ACCEPTABLE_PSYCHOLOGY_PAUSE_RATE_PCT:
        ready = False
        reasons.append(
            f"{psychology_stats.pause_rate_pct}% of check-ins hit 'pause' -- above the {MAX_ACCEPTABLE_PSYCHOLOGY_PAUSE_RATE_PCT}% threshold, discipline isn't consistent yet."
        )

    if ready:
        reasons.append(
            f"{edge_stats.total_trades} trades, profit factor {edge_stats.profit_factor}, psychology pause rate {psychology_stats.pause_rate_pct}% -- all thresholds met."
        )

    return ReadinessAssessment(
        account=account, ready=ready, edge_stats=edge_stats, psychology_stats=psychology_stats, reasons=reasons
    )


def run_performance_review(account: str) -> ReadinessAssessment:
    """Live entry point: pulls real trade + psychology history for an
    account, computes stats, assesses readiness, and publishes the
    full report to memory_knowledge. Never approves anything itself --
    this is a report for Mohamed (and eventually the CEO/Lead agent),
    the actual go/no-go decision always stays his."""
    from agents.forex._memory_helpers import safe_add_knowledge

    trades = fetch_account_trades(account)
    checkins = fetch_account_psychology_checkins(account)

    edge_stats = compute_edge_stats(trades)
    psychology_stats = compute_psychology_compliance(checkins)
    assessment = assess_readiness(account, edge_stats, psychology_stats)

    summary = (
        f"Performance review for {account}: {'READY' if assessment.ready else 'NOT READY'} for real money. "
        f"{edge_stats.total_trades} trades, {edge_stats.win_rate_pct}% win rate, "
        f"profit factor {edge_stats.profit_factor}, expectancy ${edge_stats.expectancy}/trade. "
        f"{psychology_stats.total_checkins} psychology check-ins, {psychology_stats.pause_rate_pct}% pause rate. "
        f"{' '.join(assessment.reasons)}"
    )
    safe_add_knowledge(
        division="forex",
        agent_id="forex-performance-review-v0.1",
        content=summary,
        source="performance_review",
        metadata={
            "account": account,
            "ready": assessment.ready,
            "total_trades": edge_stats.total_trades,
            "profit_factor": edge_stats.profit_factor,
            "psychology_pause_rate_pct": psychology_stats.pause_rate_pct,
        },
    )
    return assessment
