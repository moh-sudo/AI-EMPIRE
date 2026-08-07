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

v0.2 (2026-08-01): the gap above is closed -- stage_trade_proposal()
sends a proposal to Telegram AND persists it as a pending approval;
handle_trade_approval_reply() (wired into a new dedicated listener,
agents/forex/entry_exit_listener.py, mirroring the Fixera Marketing
Agent's approval flow built the same day) reacts to a real "APPROVE
<id>" / "REJECT <id>" reply from Mohamed's phone, calling
execute_order(confirmed=True) only on approval. execute_order() itself
is completely unchanged -- all three hard safety rules above still
apply exactly as before; this only replaces how confirmed=True gets
set, not what it gates. Explicitly NOT a live-fire test in itself --
per Mohamed's own instruction (2026-08-01), this is architecture only;
the actual first real order (even to the demo account) is a separate,
deliberate decision he'll make when he's ready to give it his full
attention, not something to trigger incidentally while testing plumbing.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

PENDING_PROPOSALS_FILE = Path(__file__).resolve().parent / ".pending_trade_proposals.json"
_APPROVAL_PATTERN = re.compile(r"^(APPROVE|REJECT)\s+(\S+)$", re.IGNORECASE)

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
        return ExecutionPermission(
            account=account,
            allowed=True,
            reasons=["Demo account -- always allowed, this is how the readiness track record gets built."],
        )

    if account not in REAL_ACCOUNTS:
        return ExecutionPermission(
            account=account,
            allowed=False,
            reasons=[f"'{account}' isn't a recognized demo or real account -- refusing rather than assuming safe."],
        )

    from agents.forex.performance_review import run_performance_review

    assessment = run_performance_review(account)
    if assessment.ready:
        return ExecutionPermission(account=account, allowed=True, reasons=list(assessment.reasons))
    return ExecutionPermission(
        account=account,
        allowed=False,
        reasons=[f"Performance Review: NOT READY for {account}."] + list(assessment.reasons),
    )


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
    *,
    account: str,
    pair: str,
    direction: Literal["buy", "sell"],
    lot_size: float,
    stop_loss: float,
    take_profit: float,
    strategy_name: str,
    gate_verdict: str,
    gate_reasons: list[str],
    risk_verdict: str,
    risk_notes: list[str],
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
        account=account,
        pair=pair.upper(),
        direction=direction,
        lot_size=lot_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        strategy_name=strategy_name,
        gate_verdict=gate_verdict,
        gate_reasons=list(gate_reasons),
        risk_verdict=risk_verdict,
        risk_notes=list(risk_notes),
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
        reasons.append(
            "All gates agree -- tradeable per the system's own checks. Still requires Mohamed's explicit confirmation before anything is sent to MT5."
        )

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
    """Sends a one-way notification via Entry & Exit's OWN dedicated
    bot (TELEGRAM_BOT_TOKEN) -- deliberately a different bot/token than
    CEO/Lead's routine briefings (TELEGRAM_CEO_BOT_TOKEN, see
    agents/forex/ceo_lead.py), per Mohamed's explicit request
    (2026-07-26): a real trade proposal needing his confirmation should
    never get buried under a routine market update in the same chat."""
    from agents.forex._telegram import send_telegram

    return send_telegram(message, token_env="TELEGRAM_BOT_TOKEN")


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
        return {
            "executed": False,
            "reason": "confirmed=True was not passed -- per Law 4, this agent never executes without an explicit human go-ahead.",
        }

    tradeable, reasons = is_proposal_tradeable(proposal)
    if not tradeable:
        return {"executed": False, "reason": "Proposal is not tradeable.", "details": reasons}

    import MetaTrader5 as mt5

    from agents.forex.market_analytics import connect, disconnect, resolve_symbol

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
            division="forex",
            agent_id="forex-entry-exit-v0.1",
            event_type="order_executed",
            context=f"{proposal.direction} {proposal.lot_size} {symbol} SL={proposal.stop_loss} TP={proposal.take_profit}",
            outcome="filled" if success else "rejected",
            metadata={
                "account": proposal.account,
                "strategy": proposal.strategy_name,
                "pair": symbol,
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


# ---------------------------------------------------------------------------
# Remote approval flow (added 2026-08-01). Lets Mohamed approve/reject a real
# trade proposal from his phone via Telegram -- mirrors the Fixera Marketing
# Agent's approval flow, built the same day. execute_order()'s own hard
# safety rules (confirmed=True gate, Performance Review readiness check,
# MT5 server-match check) are unchanged and still all apply -- this only
# supplies the confirmed=True flag from a real human reply instead of a
# hardcoded argument.
# ---------------------------------------------------------------------------


def _read_pending_proposals() -> dict:
    if not PENDING_PROPOSALS_FILE.exists():
        return {}
    try:
        return json.loads(PENDING_PROPOSALS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_pending_proposals(data: dict) -> None:
    PENDING_PROPOSALS_FILE.write_text(json.dumps(data, indent=2))


def _proposal_to_dict(proposal: TradeProposal) -> dict:
    return asdict(proposal)


def _proposal_from_dict(data: dict) -> TradeProposal:
    data = dict(data)
    data["execution_permission"] = ExecutionPermission(**data["execution_permission"])
    return TradeProposal(**data)


def stage_trade_proposal(proposal: TradeProposal) -> dict:
    """Sends a trade proposal to Telegram (Entry & Exit's own dedicated
    bot, TELEGRAM_BOT_TOKEN) and persists it as a pending approval.
    Never calls execute_order() itself -- publishing the proposal for
    review and actually executing it are kept as separate steps, same
    principle as the Marketing Agent's stage_post()/publish_post()
    split."""
    tradeable, reasons = is_proposal_tradeable(proposal)

    pending = _read_pending_proposals()
    next_id = str(max([int(k) for k in pending.keys()] + [0]) + 1)
    pending[next_id] = {
        "proposal": _proposal_to_dict(proposal),
        "tradeable_at_staging": tradeable,
        "status": "pending",
    }
    _save_pending_proposals(pending)

    message = format_telegram_message(proposal, tradeable, reasons)
    message += f'\n\nReply "APPROVE {next_id}" to execute, or "REJECT {next_id}" to discard.'
    send_result = send_telegram_alert(message)
    return {"proposal_id": next_id, "tradeable_at_staging": tradeable, "telegram_sent": send_result.get("sent", False)}


def handle_trade_approval_reply(text: str) -> dict | None:
    """If text matches "APPROVE <id>" or "REJECT <id>" (case-insensitive),
    acts on the matching pending proposal and returns a result dict
    with a "reply" message for entry_exit_listener.py to send back.
    Returns None for any other text. Re-runs execute_order()'s own full
    safety-check chain on approval -- never trusts the staged snapshot
    alone, since real-world conditions (gates, account readiness, which
    MT5 terminal is connected) can change between staging and reply."""
    match = _APPROVAL_PATTERN.match(text.strip())
    if not match:
        return None

    action, proposal_id = match.group(1).upper(), match.group(2)
    pending = _read_pending_proposals()
    entry = pending.get(proposal_id)
    if not entry:
        return {"handled": True, "reply": f"No pending trade proposal #{proposal_id} found."}
    if entry["status"] != "pending":
        return {"handled": True, "reply": f"Proposal #{proposal_id} was already {entry['status']}."}

    if action == "REJECT":
        entry["status"] = "rejected"
        _save_pending_proposals(pending)
        return {"handled": True, "reply": f"Trade proposal #{proposal_id} rejected -- not executed."}

    proposal = _proposal_from_dict(entry["proposal"])
    result = execute_order(proposal, confirmed=True)
    entry["status"] = "executed" if result.get("executed") else "approve_failed"
    entry["execute_result"] = result
    _save_pending_proposals(pending)
    if result.get("executed"):
        return {"handled": True, "reply": f"Proposal #{proposal_id} EXECUTED. Order ID: {result.get('order_id')}"}
    return {
        "handled": True,
        "reply": f"Proposal #{proposal_id} approved but NOT executed: {result.get('reason', result)}",
    }
