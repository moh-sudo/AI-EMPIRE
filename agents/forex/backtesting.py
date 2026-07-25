"""Backtesting Agent v0.1 -- Forex Division.

Grounded in two things Mohamed already documented: his own journal
rule ("Practicing / BACKTASTING EVERY WEEKEND") and the SMC reference
already published to memory_knowledge ("Confidence comes from
testing -- backtesting, reviewing past trades, and journaling build
real confidence, not hope").

Deliberately kept separate from Journaling Agent's real/demo trade
log: a backtest result is not a real trade, and mixing the two would
corrupt Performance Review's "is this account actually ready" signal.
Same reasoning as Journaling's account tagging -- different kinds of
history need to stay distinguishable, not blended into one pile.

Two layers, same split as Market Analytics: log_backtest_trade() and
run_backtest_stats_publish() need the DB; compute_stats() is pure
logic, fully testable without it.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional

BacktestOutcome = Literal["win", "loss", "be"]


@dataclass
class BacktestTrade:
    pair: str
    direction: str  # "buy" | "sell"
    result: BacktestOutcome
    pnl: float
    entry: Optional[float] = None
    exit: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reward_to_risk: Optional[float] = None  # the R:R this specific trade actually achieved
    setup_notes: Optional[str] = None


@dataclass
class BacktestStats:
    total_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate_pct: float
    avg_reward_to_risk: Optional[float]
    profit_factor: Optional[float]  # gross win / gross loss; None if no losses to divide by
    total_pnl: float
    expectancy: Optional[float]  # average P&L per trade
    notes: list[str] = field(default_factory=list)


def _build_backtest_context(trade: BacktestTrade) -> str:
    direction_word = "long" if trade.direction.lower() in ("buy", "long") else "short"
    parts = [f"Backtest: {trade.pair.upper()} {direction_word}"]
    if trade.entry is not None and trade.exit is not None:
        parts.append(f"entered at {trade.entry}, exited at {trade.exit}")
    if trade.stop_loss is not None:
        parts.append(f"SL {trade.stop_loss}")
    if trade.take_profit is not None:
        parts.append(f"TP {trade.take_profit}")
    if trade.reward_to_risk is not None:
        parts.append(f"achieved {trade.reward_to_risk:.1f}:1 R:R")
    context = " ".join(parts) + "."
    if trade.setup_notes:
        context += f" {trade.setup_notes}"
    return context


def log_backtest_trade(trade: BacktestTrade) -> dict:
    from agents.forex._memory_helpers import safe_add_experience

    result_word = {"win": "Win", "loss": "Loss", "be": "Breakeven"}.get(trade.result, trade.result)
    sign = "+" if trade.pnl >= 0 else ""

    return safe_add_experience(
        division="forex",
        agent_id="forex-backtesting-v0.1",
        event_type="backtest_trade",
        context=_build_backtest_context(trade),
        outcome=f"{result_word} -- {sign}${trade.pnl:,.2f}",
        metadata={
            "pair": trade.pair.upper(), "direction": trade.direction, "result": trade.result,
            "pnl": trade.pnl, "entry": trade.entry, "exit": trade.exit,
            "stop_loss": trade.stop_loss, "take_profit": trade.take_profit,
            "reward_to_risk": trade.reward_to_risk,
        },
    )


def compute_stats(trades: list[BacktestTrade]) -> BacktestStats:
    """Pure logic, no DB dependency -- fully unit-testable. Computes
    the numbers that actually answer "does this rule set have a real
    edge": win rate, profit factor, average achieved R:R, expectancy.
    Reports the numbers plainly rather than inventing arbitrary
    quality tiers ("great"/"bad") that weren't given by Mohamed --
    profit factor > 1 means gross wins outweigh gross losses, that's
    the only judgment made here."""
    if not trades:
        return BacktestStats(0, 0, 0, 0, 0.0, None, None, 0.0, None, notes=["No trades to compute stats from."])

    wins = [t for t in trades if t.result == "win"]
    losses = [t for t in trades if t.result == "loss"]
    breakevens = [t for t in trades if t.result == "be"]

    total = len(trades)
    win_rate = (len(wins) / total) * 100 if total else 0.0

    rr_values = [t.reward_to_risk for t in trades if t.reward_to_risk is not None]
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else None

    gross_win = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else None

    total_pnl = sum(t.pnl for t in trades)
    expectancy = total_pnl / total if total else None

    notes: list[str] = []
    if profit_factor is not None:
        notes.append(
            f"Profit factor {profit_factor:.2f} -- {'gross wins outweigh gross losses' if profit_factor > 1 else 'gross losses outweigh gross wins'} over this sample."
        )
    elif gross_loss == 0 and gross_win > 0:
        notes.append("No losing trades in this sample -- profit factor undefined (nothing to divide by).")

    # 30 is a commonly-used general statistical minimum sample size,
    # not a number Mohamed specified -- flagged as a general heuristic,
    # not an authoritative rule from his own material.
    if total < 30:
        notes.append(f"Only {total} trades in this sample -- a common statistical rule of thumb wants 30+ before treating a win rate or profit factor as reliable.")

    return BacktestStats(
        total_trades=total, wins=len(wins), losses=len(losses), breakevens=len(breakevens),
        win_rate_pct=round(win_rate, 2),
        avg_reward_to_risk=round(avg_rr, 2) if avg_rr is not None else None,
        profit_factor=round(profit_factor, 2) if profit_factor is not None else None,
        total_pnl=round(total_pnl, 2),
        expectancy=round(expectancy, 2) if expectancy is not None else None,
        notes=notes,
    )


def run_backtest_stats_publish(trades: list[BacktestTrade]) -> dict:
    """Live entry point: computes stats over a batch of backtest
    trades and publishes the summary to memory_knowledge, so it's
    queryable as a running reference alongside the strategy docs --
    "does the rule set actually work" becomes a real, checkable fact,
    not a feeling."""
    from agents.forex._memory_helpers import safe_add_knowledge

    stats = compute_stats(trades)
    summary = (
        f"Backtest stats over {stats.total_trades} trades: "
        f"win rate {stats.win_rate_pct}%, profit factor {stats.profit_factor}, "
        f"avg achieved R:R {stats.avg_reward_to_risk}, total P&L ${stats.total_pnl:,.2f}, "
        f"expectancy ${stats.expectancy}/trade. {' '.join(stats.notes)}"
    )
    return safe_add_knowledge(
        division="forex",
        agent_id="forex-backtesting-v0.1",
        content=summary,
        source="backtest_stats",
        metadata={
            "total_trades": stats.total_trades, "win_rate_pct": stats.win_rate_pct,
            "profit_factor": stats.profit_factor, "expectancy": stats.expectancy,
        },
    )
