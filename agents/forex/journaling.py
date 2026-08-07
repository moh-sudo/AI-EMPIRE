"""Journaling Agent v0.1 -- Forex Division ("Trade Journal").

Per the real design (roadmap doc section 5.4): "Trade Journal:
automated logging of trade decisions, entry/exit, P&L to
memory_experience." This is that agent, explicitly named in the spec
(unlike most of the other 8, which were Mohamed's own deliberate
addition on top of the base design).

Two kinds of entries, mirroring both Mohamed's handwritten journal
(reflective entries: mistake/profit/lesson/psychology/general, same
categories his TradeTrack tool already uses) and the actual trade
record (pair, direction, result, P&L, entry/exit, session, strategy):
  - log_trade(): a closed trade, written as a natural-language context
    string (what gets embedded and later semantically searched) plus
    structured metadata for exact filtering/stats.
  - log_reflection(): a freeform reflective entry, same five type
    categories his existing tools already use.
"""

from dataclasses import dataclass
from typing import Literal

ReflectionType = Literal["mistake", "profit", "lesson", "psychology", "general"]
TradeResult = Literal["win", "loss", "be"]


@dataclass
class TradeLogEntry:
    account: str  # e.g. "exness_demo", "fundednext_stellar_lite_10k" -- every trade belongs to a specific account
    pair: str
    direction: str  # "buy" | "sell"
    result: TradeResult
    pnl: float
    session: str | None = None
    strategy: str | None = None
    entry: float | None = None
    exit: float | None = None
    lot: float | None = None
    notes: str | None = None


def _build_trade_context(trade: TradeLogEntry) -> str:
    direction_word = "long" if trade.direction.lower() in ("buy", "long") else "short"
    parts = [f"{trade.pair.upper()} {direction_word}", f"on {trade.account}"]
    if trade.session:
        parts.append(f"during {trade.session} session")
    if trade.strategy:
        parts.append(f"using {trade.strategy}")
    if trade.entry is not None and trade.exit is not None:
        parts.append(f"entered at {trade.entry}, exited at {trade.exit}")
    if trade.lot is not None:
        parts.append(f"lot size {trade.lot}")
    context = " ".join(parts) + "."
    if trade.notes:
        context += f" {trade.notes}"
    return context


def _build_trade_outcome(trade: TradeLogEntry) -> str:
    result_word = {"win": "Win", "loss": "Loss", "be": "Breakeven"}.get(trade.result, trade.result)
    sign = "+" if trade.pnl >= 0 else ""
    return f"{result_word} -- {sign}${trade.pnl:,.2f}"


def log_trade(trade: TradeLogEntry) -> dict:
    from agents.forex._memory_helpers import safe_add_experience

    return safe_add_experience(
        division="forex",
        agent_id="forex-journaling-v0.1",
        event_type="trade_closed",
        context=_build_trade_context(trade),
        outcome=_build_trade_outcome(trade),
        metadata={
            "account": trade.account,
            "pair": trade.pair.upper(),
            "direction": trade.direction,
            "result": trade.result,
            "pnl": trade.pnl,
            "session": trade.session,
            "strategy": trade.strategy,
            "entry": trade.entry,
            "exit": trade.exit,
            "lot": trade.lot,
        },
    )


def log_reflection(
    *,
    reflection_type: ReflectionType,
    title: str,
    body: str,
    account: str | None = None,
    pinned: bool = False,
) -> dict:
    """account is optional here (unlike log_trade, where every trade
    belongs to exactly one account) since a reflection can be general
    trading psychology, not tied to a single account's activity."""
    from agents.forex._memory_helpers import safe_add_experience

    return safe_add_experience(
        division="forex",
        agent_id="forex-journaling-v0.1",
        event_type="journal_reflection",
        context=f"{title}\n\n{body}",
        outcome=reflection_type,
        metadata={"reflection_type": reflection_type, "title": title, "pinned": pinned, "account": account},
    )
