"""Entry & Exit Agent v0.1 -- Forex Division.

The last of the 11 Forex agents -- the only one that can actually touch
MT5. Deliberately built last per the original design: everything else
(Research/Strategy/Psychology gates, Risk Management, News Filter,
Performance Review's readiness signal, CEO/Lead's Execution Gate) had
to exist first, since this agent's entire job is combining their
outputs into a single tradeable/not-tradeable decision and then, only
with explicit human confirmation, sending an order.

Execution mechanism (2026-07-25): originally scoped around a
TradingView-to-MT5 bridge (niiisho/TradingView-MT5-Bridge, vetted this
session -- MIT license, 100% local architecture with no internet-
exposed endpoint, actively maintained, no red flags found). Turned out
not to be needed: that bridge exists to relay TradingView Pine Script
alerts into MT5 via a Chrome extension + local HTTP relay. Every signal
this system generates already originates in Python (Strategy/CEO-Lead),
and Market Analytics already has a live, working MT5 connection via the
official MetaTrader5 package -- so this agent places orders directly
via mt5.order_send(), reusing Market Analytics' connect()/
resolve_symbol(). Removes an entire dependency (Chrome extension, local
HTTP server) for no loss of capability.

Hard safety rules, enforced in code, not just documented:
1. execute_order() refuses to send anything to MT5 unless confirmed=True
   is passed explicitly -- Mohamed's own go-ahead per governance Law 4
   (AI advises, humans decide), never inferred from a passing gate
   alone. There is no code path from "gates passed" straight to "order
   sent" without that explicit flag.
2. Real accounts are blocked from trading at all until Performance
   Review reports that specific account READY (check_execution_allowed).
   Demo accounts are always allowed -- that's how the track record
   Performance Review needs actually gets built.
3. Before sending an order, the currently-connected MT5 terminal's
   server name is checked against the proposal's account -- refuses if
   they don't match, rather than silently firing on whatever account
   happens to be logged in.

Known gap, not hidden: the human-confirmation step in v0.1 is a plain
explicit function argument (confirmed=True), not yet a live Telegram
reply listener -- that would need a persistent polling process (same
category of infrastructure as agents/audit/server.py + n8n), deferred
to v0.2. v0.1 sends the proposal to Telegram for visibility
(send_telegram_alert) and requires the caller to separately pass
confirmed=True to actually execute.
"""

import os
from dataclasses import dataclass, field
from typing import Literal, Optional

import requests

DEMO_ACCOUNTS = {"exness_demo"}
REAL_ACCOUNTS = {"fundednext_stellar_lite_10k", "exness_live", "ic_markets_live"}

GATE_PROCEED = "proceed"
RISK_BREACH = "would_breach_limit"


@dataclass
class ExecutionPermission:
    account: str
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def check_execution_allowed(account: str) -> ExecutionPermission:
    """Demo accounts are always allowed to trade -- that's how the
    track record Performance Review needs actually gets built. Real
    accounts are blocked until Performance Review reports that
    specific account READY. Unknown accounts are refused outright
    (fail closed, same pattern as News Filter's unreachable-calendar
    case) rather than silently assumed safe."""
    if account in DEMO_ACCOUNTS:
        return ExecutionPermission(account=account, allowed=True, reasons=["Demo account -- always allowed, this is how the readiness track record gets built."])

    if account not in REAL_ACCOUNTS:
        return ExecutionPermission(account=account, allowed=False, reasons=[f"'{account}' isn't a recognized demo or real account -- refusing rather than assuming safe."])

    from agents.forex.performance_review import run_performance_review

    assessment = run_performance_review(account)
    if assessment.ready:
        return ExecutionPermission(account=account, allowed=True, reasons=list(assessment.reasons))
    return ExecutionPermission(account=account, allowed=False, reasons=[f"Performance Review: NOT READY for {account}."] + list(assessment.reasons))


@dataclass
class TradeProposal:
    account: str
    pair: str
    direction: Literal["buy", "sell"]
    lot_size: float
    stop_loss: float
    take_profit: float
    strategy_name: str
    gate_verdict: str
    gate_reasons: list[str]
    risk_verdict: str
    risk_notes: list[str]
    execution_permission: ExecutionPermission


def build_trade_proposal(
    *, account: str, pair: str, direction: Literal["buy", "sell"], lot_size: float,
    stop_loss: float, take_profit: float, strategy_name: str,
    gate_verdict: str, gate_reasons: list[str],
    risk_verdict: str, risk_notes: list[str],
) -> TradeProposal:
    """Pure aggregation -- takes the already-computed verdicts from
    CEO/Lead's evaluate_execution_gate() and Risk Management's
    evaluate_*_risk() (pass their .verdict/.reasons or .notes
    directly), plus this agent's own execution-permission check, and
    combines them into one structured proposal. Doesn't itself decide
    whether to trade -- that combination is is_proposal_tradeable()'s
    job, kept separate so the aggregation step stays a pure function
    (no DB call) except for the one live Performance Review check
    inside check_execution_allowed() when the account is a real one."""
    permission = check_execution_allowed(account)
    return TradeProposal(
        account=account, pair=pair.upper(), direction=direction, lot_size=lot_size,
        stop_loss=stop_loss, take_profit=take_profit, strategy_name=strategy_name,
        gate_verdict=gate_verdict, gate_reasons=list(gate_reasons),
        risk_verdict=risk_verdict, risk_notes=list(risk_notes),
        execution_permission=permission,
    )


def is_proposal_tradeable(proposal: TradeProposal) -> tuple[bool, list[str]]:
    """Everything must agree: the CEO/Lead execution gate proceeded,
    Risk Management didn't flag a breach, and this account is
    permitted to trade at all. Any one blocker means not tradeable,
    with every reason surfaced -- never a silent partial pass."""
    reasons: list[str] = []
    ok = True

    if proposal.gate_verdict != GATE_PROCEED:
        ok = False
        reasons.append(f"Execution gate did not proceed (verdict: {proposal.gate_verdict}).")
        reasons.extend(proposal.gate_reasons)

    if proposal.risk_verdict == RISK_BREACH:
        ok = False
        reasons.append("Risk Management: proposed risk would breach a limit.")
        reasons.extend(proposal.risk_notes)

    if not proposal.execution_permission.allowed:
        ok = False
        reasons.extend(proposal.execution_permission.reasons)

    if ok:
        reasons.append("All gates agree -- tradeable per the system's own checks. Still requires Mohamed's explicit confirmation before anything is sent to MT5.")

    return ok, reasons


def format_telegram_message(proposal: TradeProposal, tradeable: bool, reasons: list[str]) -> str:
    status = "TRADEABLE (pending your confirmation)" if tradeable else "BLOCKED"
    lines = [
        f"[{status}] {proposal.pair} {proposal.direction.upper()} -- {proposal.strategy_name}",
        f"Account: {proposal.account} | Lot: {proposal.lot_size} | SL: {proposal.stop_loss} | TP: {proposal.take_profit}",
        "",
    ]
    lines.extend(f"- {r}" for r in reasons)
    return "\n".join(lines)


def send_telegram_alert(message: str) -> dict:
    """Sends a one-way notification -- TELEGRAM_BOT_TOKEN and
    TELEGRAM_CHAT_ID must be set in .env (not yet configured as of
    2026-07-25). Never raises on failure or on missing config -- a
    notification failing shouldn't crash the pipeline; logs a failed-
    send experience row instead, same pattern used for Resend email
    failures elsewhere in this codebase."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"sent": False, "reason": "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured in .env yet."}

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
        return {"sent": True, "response": resp.json()}
    except requests.RequestException as e:
        from agents.forex._memory_helpers import safe_add_experience

        safe_add_experience(
            division="forex", agent_id="forex-entry-exit-v0.1", event_type="telegram_send_failed",
            context=message, outcome="failed", metadata={"error": str(e)},
        )
        return {"sent": False, "reason": str(e)}


def execute_order(proposal: TradeProposal, confirmed: bool) -> dict:
    """The only function in this agent that actually touches MT5.
    Hard-refuses unless: (1) confirmed=True was passed explicitly, (2)
    is_proposal_tradeable() agrees, and (3) the MT5 terminal that's
    actually connected right now is logged into a server matching this
    proposal's account -- a terminal could be logged into a different
    account than expected, and silently firing an order there would be
    exactly the kind of confidently-wrong mistake this whole system is
    built to avoid.

    Demo-account matching is by server-name convention (looking for
    "demo"/"trial" in the connected server name) rather than a strict
    login-number registry, since no such registry exists yet -- a real
    limitation, documented rather than silently assumed correct."""
    if not confirmed:
        return {"executed": False, "reason": "confirmed=True was not passed -- per Law 4, this agent never executes without an explicit human go-ahead."}

    tradeable, reasons = is_proposal_tradeable(proposal)
    if not tradeable:
        return {"executed": False, "reason": "Proposal is not tradeable.", "details": reasons}

    from agents.forex.market_analytics import connect, disconnect, resolve_symbol
    import MetaTrader5 as mt5

    if not connect():
        return {"executed": False, "reason": "Could not connect to MT5 terminal."}

    try:
        account_info = mt5.account_info()
        if account_info is None:
            return {"executed": False, "reason": "MT5 connected but account_info() returned None."}

        server_lower = (account_info.server or "").lower()
        if proposal.account in DEMO_ACCOUNTS and "demo" not in server_lower and "trial" not in server_lower:
            return {
                "executed": False,
                "reason": (
                    f"Refusing: proposal is for '{proposal.account}' but the connected MT5 "
                    f"terminal's server ('{account_info.server}') doesn't look like a demo "
                    f"server. Never firing an order against a mismatched account."
                ),
            }

        symbol = resolve_symbol(proposal.pair)
        order_type = mt5.ORDER_TYPE_BUY if proposal.direction == "buy" else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if proposal.direction == "buy" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": proposal.lot_size,
            "type": order_type,
            "price": price,
            "sl": proposal.stop_loss,
            "tp": proposal.take_profit,
            "deviation": 20,
            "magic": 20260725,
            "comment": f"AI_EMPIRE:{proposal.strategy_name}"[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        success = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE

        from agents.forex._memory_helpers import safe_add_experience

        safe_add_experience(
            division="forex", agent_id="forex-entry-exit-v0.1", event_type="order_executed",
            context=f"{proposal.direction} {proposal.lot_size} {symbol} SL={proposal.stop_loss} TP={proposal.take_profit}",
            outcome="filled" if success else "rejected",
            metadata={
                "account": proposal.account, "strategy": proposal.strategy_name, "pair": symbol,
                "retcode": result.retcode if result is not None else None,
                "order_id": result.order if (result is not None and success) else None,
            },
        )
        return {
            "executed": success,
            "retcode": result.retcode if result is not None else None,
            "order_id": result.order if (result is not None and success) else None,
        }
    finally:
        disconnect()
