"""CEO/Lead Agent v0.1 -- Forex Division.

Per governance Law 12 (Chain of Command & Agent Authority Matrix) and
the real Forex Division design (Execution Gate: Research + Technical
Analysis + Trading Psychology all required before a trade proceeds,
never silent rejection, always reaches Mohamed per Law 4): this agent
sits above the other 9 Forex agents, aggregating their outputs into
one coherent view rather than nine separate pings, and implements the
actual Execution Gate combination logic.

Work Quality Authority, not Constitutional Authority (Law 12): this
agent can hold a signal back (treat a failed gate as "not ready") but
never approves a trade itself -- that's Mohamed's call, always. A
genuine cross-agent contradiction (Deadlock Protocol) always escalates
rather than being silently resolved either way.
"""

from dataclasses import dataclass, field
from typing import Optional

GATE_PROCEED = "proceed"
GATE_PAUSE = "pause"
GATE_DEADLOCK = "deadlock"  # a genuine cross-agent contradiction, distinct from one gate simply failing


@dataclass
class GateInput:
    name: str  # e.g. "research", "strategy", "psychology", "risk_management", "news_filter"
    passed: bool
    detail: str


@dataclass
class ExecutionGateResult:
    verdict: str  # proceed | pause | deadlock
    inputs: list[GateInput] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def evaluate_execution_gate(inputs: list[GateInput]) -> ExecutionGateResult:
    """The actual Execution Gate: every input must pass for a trade to
    proceed. Never silently rejects -- names which gate(s) failed and
    why, meant to always reach Mohamed regardless of outcome (Law 4).
    'proceed' means every agent agrees the setup is ready -- the
    actual trade action is Entry & Exit's job (not yet built) and
    ultimately Mohamed's decision, this never executes anything."""
    if not inputs:
        return ExecutionGateResult(verdict=GATE_PAUSE, reasons=["No gate inputs provided -- nothing to evaluate."])

    failed = [i for i in inputs if not i.passed]
    reasons: list[str] = []

    if not failed:
        reasons.append(f"All {len(inputs)} gates passed: {', '.join(i.name for i in inputs)}.")
        return ExecutionGateResult(verdict=GATE_PROCEED, inputs=inputs, reasons=reasons)

    for f in failed:
        reasons.append(f"{f.name}: {f.detail}")

    return ExecutionGateResult(verdict=GATE_PAUSE, inputs=inputs, reasons=reasons)


def check_cross_agent_agreement(strategy_trend: Optional[str], market_analytics_trend: Optional[str]) -> Optional[str]:
    """Deadlock Protocol trigger: a genuine Logic Disagreement between
    two agents reasoning about the same underlying fact (e.g. Strategy
    asserts a bullish bias but Market Analytics' independently-
    computed structure read says downtrend) -- distinct from a normal
    failed gate, and per Law 12 this should pause and escalate rather
    than let either side silently win. Returns a description of the
    disagreement, or None if they agree or either is unknown (you
    can't disagree with "unknown")."""
    if not strategy_trend or not market_analytics_trend:
        return None
    bullish_names = {"uptrend", "bullish"}
    bearish_names = {"downtrend", "bearish"}
    if strategy_trend in bullish_names and market_analytics_trend in bearish_names:
        return f"Strategy asserts {strategy_trend} but Market Analytics' independent structure read says {market_analytics_trend} -- genuine disagreement, not just a failed gate."
    if strategy_trend in bearish_names and market_analytics_trend in bullish_names:
        return f"Strategy asserts {strategy_trend} but Market Analytics' independent structure read says {market_analytics_trend} -- genuine disagreement, not just a failed gate."
    return None


def run_daily_briefing() -> dict:
    """Live entry point: calls Research, News Filter, Market Analytics,
    and Performance Review, aggregates into one combined report, and
    logs it as the CEO/Lead's own coordination output -- the single
    voice Mohamed actually reads, instead of separate agent pings.

    Broad exception handling here is deliberate, not a shortcut: this
    is the top of the call stack whose entire job is "don't let one
    sub-system's failure take down the whole briefing" -- the same
    fail-safe principle used throughout the division (Research/News
    Filter never crash on a single feed outage), just applied one
    level higher, across whole agents rather than within one."""
    from agents.forex._memory_helpers import safe_add_knowledge

    sections: list[str] = []

    try:
        from agents.forex.research import run_research_sweep

        report = run_research_sweep()
        sections.append(f"RESEARCH:\n{report.summary_text()}")
    except Exception as e:
        sections.append(f"RESEARCH: unavailable ({e})")

    try:
        from agents.forex.news_filter import run_news_check_sweep

        news_results = run_news_check_sweep()
        paused = [r for r in news_results if r.should_pause]
        if paused:
            sections.append("NEWS FILTER:\n" + "\n".join(f"  {r.pair}: PAUSE" for r in paused))
        else:
            sections.append("NEWS FILTER: no imminent high-impact news on any traded pair.")
    except Exception as e:
        sections.append(f"NEWS FILTER: unavailable ({e})")

    try:
        from agents.forex.market_analytics import run_market_analytics_sweep

        structure_results = run_market_analytics_sweep()
        if structure_results:
            sections.append("MARKET ANALYTICS:\n" + "\n".join(f"  {pair}: {r.trend}" for pair, r in structure_results.items()))
        else:
            sections.append("MARKET ANALYTICS: unavailable (MT5 not connected).")
    except Exception as e:
        sections.append(f"MARKET ANALYTICS: unavailable ({e})")

    try:
        from agents.forex.performance_review import run_performance_review

        assessment = run_performance_review("exness_demo")
        sections.append(
            f"PERFORMANCE REVIEW (exness_demo): {'READY' if assessment.ready else 'NOT READY'} -- "
            f"{assessment.edge_stats.total_trades} trades logged."
        )
    except Exception as e:
        sections.append(f"PERFORMANCE REVIEW: unavailable ({e})")

    summary = "Forex Division Daily Briefing (CEO/Lead Agent)\n\n" + "\n\n".join(sections)

    safe_add_knowledge(
        division="forex",
        agent_id="forex-ceo-lead-v0.1",
        content=summary,
        source="daily_briefing",
        metadata={"section_count": len(sections)},
    )
    return {"summary": summary, "sections": sections}
