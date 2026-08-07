"""Strategy Agent v0.1 -- Forex Division.

Per the real design (governance doc section 3.1): this is the
Technical Analysis stage (30% weight) -- produces a Trade Plan
(Entry/Stop/Target/Risk) with status Validated/Ready/Pending/Rejected.
Per Mohamed's own request, kept as its own agent distinct from Market
Analytics: this one owns "which strategy (SMC or ICT)" and whether a
described setup actually follows it.

There is no live chart/price feed wired yet (Market Analytics is
blocked on the TradingView data-access decision -- webhook push vs.
independent pull, still open). So this agent's real, non-mock job
right now is: encode Mohamed's actual strategy rules (from his
handwritten trading journal, "JOURNEY OF MY FOREX TRADING.docx") as a
structured checklist, and validate a *described* setup against it --
deterministic keyword/criteria matching, not guessing. Once Market
Analytics exists, its structured chart-read output can be fed through
the same validate_setup() instead of free text.
"""

from dataclasses import dataclass, field

# Mohamed's actual traded instruments -- expanded 2026-07-26 (originally
# narrowed down from a longer list "because I understand more", journal
# Week 2). Single source of truth now lives in agents/forex/_pairs.py
# alongside the per-pair trading-day schedule and priority tier.
from agents.forex._pairs import PRIORITY_PAIRS, TRADED_PAIRS

# Session windows in NY time, exactly as documented in the journal.
SESSION_WINDOWS = {
    "Asian": ("20:00", "05:00"),
    "London": ("02:00", "11:00"),
    "New York": ("08:00", "17:00"),  # journal said 5AM, almost certainly a typo for 5PM
}

# The ICT/SMC concepts Mohamed's journal names explicitly as what he
# looks for, top-down: daily/weekly bias -> drop to 4H/1H for
# structure -> FVG/BOS/CHOCH/OB -> liquidity points/POI -> premium
# (0.5-1.0) vs discount pricing.
REQUIRED_CONCEPTS = {
    "bias": ["bias", "daily bias", "weekly bias", "htf bias", "direction"],
    "structure": ["bos", "break of structure", "choch", "change of character"],
    "poi": ["fvg", "fair value gap", "ob", "order block", "liquidity", "poi", "point of interest"],
    "pricing_zone": ["premium", "discount"],
}

STATUS_VALIDATED = "Validated"
STATUS_PENDING = "Pending"
STATUS_REJECTED = "Rejected"


@dataclass
class TradePlanValidation:
    pair: str
    session: str | None
    status: str
    matched_concepts: list[str] = field(default_factory=list)
    missing_concepts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _matches_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def validate_setup(description: str, pair: str, session: str | None = None) -> TradePlanValidation:
    """Deterministic check of a described setup against Mohamed's own
    documented ICT/SMC criteria -- never invents a verdict, only
    reports which required concepts were and weren't present in the
    description, plus hard blockers (wrong pair, no session given)."""
    notes: list[str] = []
    matched: list[str] = []
    missing: list[str] = []

    pair_upper = pair.upper()
    if pair_upper not in TRADED_PAIRS:
        notes.append(
            f"{pair_upper} is not in Mohamed's traded pairs list ({', '.join(sorted(TRADED_PAIRS))}) -- outside documented experience."
        )

    if not session:
        notes.append("No session given -- a setup can't be validated without knowing which session it's in.")
    elif session not in SESSION_WINDOWS:
        notes.append(f"Session '{session}' is not one of the three documented sessions (Asian/London/New York).")

    for concept, keywords in REQUIRED_CONCEPTS.items():
        if _matches_any(description, keywords):
            matched.append(concept)
        else:
            missing.append(concept)

    if pair_upper not in TRADED_PAIRS or not session:
        status = STATUS_REJECTED
    elif missing:
        status = STATUS_PENDING
        notes.append(
            f"Missing documented concepts: {', '.join(missing)} -- setup isn't fully described per Mohamed's own checklist yet."
        )
    else:
        status = STATUS_VALIDATED

    return TradePlanValidation(
        pair=pair_upper,
        session=session,
        status=status,
        matched_concepts=matched,
        missing_concepts=missing,
        notes=notes,
    )


STRATEGY_REFERENCE_TEXT = """ICT/SMC strategy reference (Mohamed's own documented approach):
Top-down process: open daily/weekly timeframe first to establish market bias/direction,
then drop to 4H/1H for structure. Look for FVG (Fair Value Gap), BOS (Break of Structure),
CHOCH (Change of Character), OB (Order Block), and liquidity points/POI (Point of Interest).
A clean 4H FVG can act as a magnet for price. Sellers sell at premium (0.5-1.0 ratio of the
range); buyers buy at discount. Price often sweeps a prior daily high/low (liquidity) before
reversing toward the main FVG. Traded pairs: EURUSD, GBPUSD, USDCAD, XAUUSD, NAS100 (also
monitors DXY for dollar strength context). Trading sessions (NY time): Asian 8PM-5AM,
London 2AM-11AM, New York 8AM-5PM."""


def run_strategy_reference_publish() -> dict:
    """Live entry point: publishes the strategy reference to
    memory_knowledge once, so other Forex agents (and eventually the
    CEO/Lead agent) can query it as shared context. Idempotent in
    spirit -- safe to call again if the strategy notes are refined."""
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=STRATEGY_REFERENCE_TEXT,
        source="JOURNEY OF MY FOREX TRADING.docx",
        metadata={"traded_pairs": sorted(TRADED_PAIRS), "sessions": list(SESSION_WINDOWS.keys())},
    )


# ─────────────────────────────────────────────────────────────────
# SMC deep reference + structured 12-item entry checklist
# (Mohamed-provided, 2026-07-24) -- distinct source from the journal
# above, so kept as a separate memory_knowledge entry. This is the
# more precise, discrete-input companion to validate_setup()'s
# free-text matching: same spirit as Psychology's pre_trade_checklist.
# ─────────────────────────────────────────────────────────────────

SMC_REFERENCE_TEXT = """Smart Money Concepts (SMC) reference:
Core principle: price moves from liquidity to liquidity -- institutions need large buy/sell
volume to fill positions, so price often seeks areas where retail stop-losses/pending orders
cluster before reversing.
Analysis order: 1) Market Structure (HH/HL = uptrend, LH/LL = downtrend -- if structure is
unknown, don't trade). 2) BOS (Break of Structure) confirms trend continuation. 3) CHoCH
(Change of Character) warns of possible reversal. 4) Liquidity -- equal highs/lows, swing
points, trendline stops; a Liquidity Sweep is price pushing through these to trigger stops
before reversing. 5) Order Blocks -- last opposite candle before a strong move; price often
returns to it. 6) Fair Value Gap (FVG) -- an imbalance from a fast move; price often returns
to fill it; FVGs often align with Order Blocks. 7) Premium/Discount -- measured via Fibonacci
retracement of a swing; below 50% = discount (buy), above 50% = premium (sell) -- buy cheap,
sell expensive. 8) Mitigation -- price returning to complete unfilled orders at a prior zone.
9) Inducement -- a fake breakout that traps retail before the real institutional move. 10)
Internal vs External Liquidity -- internal = small in-range highs/lows, external = major
swing highs/lows; institutions usually target external liquidity. 11) Timeframe alignment --
Weekly to Daily to 4H to 1H to 15M to 5M; higher timeframe gives direction, lower gives entry.
12) Session timing -- London Open, New York Open, and the London-New York overlap carry the
highest institutional liquidity. 13) Displacement -- strong impulsive candles signal
institutional participation and often create FVGs. 14) Entry confirmation sequence: liquidity
sweep -> CHoCH -> Order Block -> Fair Value Gap -> entry. 15) Risk management -- risk only
0.5-1% of account per trade to survive inevitable losing streaks.
Foundational 5 to master first: Market Structure, BOS/CHoCH, Liquidity/Sweeps, Order Blocks,
Fair Value Gaps. Caveat: SMC concepts (order blocks, liquidity grabs) are interpretations of
price action, not universally proven mechanics -- value comes from applying a consistent,
testable rule set over many trades, not assuming every identified pattern will work."""

# Mohamed's own personal minimum (2026-07-24) -- stricter than the
# reference material's 2:1 minimum, same pattern as Risk Management's
# $250 personal daily-loss line vs FundedNext's actual $400 rule.
MOHAMED_MIN_REWARD_TO_RISK = 3.0

SMC_CHECKLIST_ITEMS: dict[str, str] = {
    "htf_trend": "What is the higher-timeframe trend?",
    "structure_identified": "Is market structure (HH/HL or LH/LL) identified?",
    "bos_or_choch": "Has there been a BOS or CHoCH?",
    "liquidity_located": "Is liquidity located (equal highs/lows, swing points)?",
    "liquidity_swept": "Has liquidity already been swept?",
    "at_order_block": "Is price at an Order Block?",
    "fvg_present": "Is there a Fair Value Gap?",
    "pricing_zone_correct": "Is price in the correct zone for the trade direction (discount for buys, premium for sells)?",
    "active_session": "Is the trade during an active market session (London/NY/overlap)?",
    "reward_to_risk_ok": "Does the trade offer at least Mohamed's own 1:3 (risk:reward) minimum?",
    "stop_loss_defined": "Is the stop-loss defined?",
    "take_profit_defined": "Is the take-profit defined (often the next liquidity pool)?",
}


@dataclass
class SMCChecklistResult:
    status: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def smc_entry_checklist(
    *,
    htf_trend: str | None = None,  # "bullish" | "bearish" | "ranging"
    structure_identified: bool = False,
    bos_or_choch: bool = False,
    liquidity_located: bool = False,
    liquidity_swept: bool = False,
    at_order_block: bool = False,
    fvg_present: bool = False,
    direction: str | None = None,  # "buy" | "sell"
    pricing_zone: str | None = None,  # "premium" | "discount"
    active_session: bool = False,
    reward_to_risk: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> SMCChecklistResult:
    """The 12-item SMC entry checklist, as discrete typed inputs
    rather than free text -- higher precision than validate_setup(),
    including a real reward:risk number and a direction-vs-pricing-
    zone consistency check (buying at premium or selling at discount
    directly contradicts the "buy cheap, sell expensive" principle)."""
    passed: list[str] = []
    failed: list[str] = []
    notes: list[str] = []

    if not htf_trend or htf_trend == "ranging":
        failed.append("htf_trend")
        notes.append("Higher-timeframe trend unknown or ranging -- 'if you don't know market structure, don't trade.'")
    else:
        passed.append("htf_trend")

    for key, ok in [
        ("structure_identified", structure_identified),
        ("bos_or_choch", bos_or_choch),
        ("liquidity_located", liquidity_located),
        ("liquidity_swept", liquidity_swept),
        ("at_order_block", at_order_block),
        ("fvg_present", fvg_present),
        ("active_session", active_session),
    ]:
        (passed if ok else failed).append(key)
        if not ok:
            notes.append(f"{SMC_CHECKLIST_ITEMS[key]} -- not confirmed.")

    zone_matches_direction = (direction == "buy" and pricing_zone == "discount") or (
        direction == "sell" and pricing_zone == "premium"
    )
    if direction and pricing_zone and zone_matches_direction:
        passed.append("pricing_zone_correct")
    else:
        failed.append("pricing_zone_correct")
        if direction and pricing_zone:
            notes.append(
                f"Direction '{direction}' at a '{pricing_zone}' zone contradicts buy-cheap/sell-expensive -- a {('buy' if direction == 'buy' else 'sell')} setup should be at {'discount' if direction == 'buy' else 'premium'}."
            )
        else:
            notes.append("Direction and/or pricing zone not given -- can't confirm buy-cheap/sell-expensive alignment.")

    if reward_to_risk is not None and reward_to_risk >= MOHAMED_MIN_REWARD_TO_RISK:
        passed.append("reward_to_risk_ok")
    else:
        failed.append("reward_to_risk_ok")
        notes.append(
            f"Reward:risk is {reward_to_risk if reward_to_risk is not None else 'not given'} -- your own minimum is {MOHAMED_MIN_REWARD_TO_RISK:.0f}:1 (stricter than the reference material's 2:1)."
        )

    if stop_loss is not None:
        passed.append("stop_loss_defined")
    else:
        failed.append("stop_loss_defined")
        notes.append("Stop-loss not defined.")

    if take_profit is not None:
        passed.append("take_profit_defined")
    else:
        failed.append("take_profit_defined")
        notes.append("Take-profit not defined.")

    if "htf_trend" in failed:
        status = STATUS_REJECTED
    elif len(failed) >= 4:
        status = STATUS_REJECTED
    elif failed:
        status = STATUS_PENDING
    else:
        status = STATUS_VALIDATED
        notes.append("All 12 checklist items confirmed.")

    return SMCChecklistResult(status=status, passed=passed, failed=failed, notes=notes)


def run_smc_reference_publish() -> dict:
    """Live entry point: publishes the SMC deep reference to
    memory_knowledge (division=forex), separate entry from the
    journal-sourced strategy reference since the source differs."""
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=SMC_REFERENCE_TEXT,
        source="mohamed-provided-2026-07-24",
        metadata={"checklist_items": list(SMC_CHECKLIST_ITEMS.keys())},
    )


# ─────────────────────────────────────────────────────────────────
# ICT deep reference (Mohamed-provided, 2026-07-24) -- ICT is the
# broader methodology SMC popularized from; adds concepts SMC doesn't
# cover (PD Arrays, OTE, Dealing Range, Daily Bias distinct from HTF
# trend, Kill Zones, Judas Swing, SMT Divergence, Power of Three).
# smc_entry_checklist() already covers the concepts the two share
# (structure, liquidity, OB, FVG, premium/discount, session, R:R,
# stop/target); the ICT-only additions (displacement, daily bias,
# specific liquidity targeting) aren't yet their own checklist
# function -- deliberately not extending the tested SMC checklist for
# this pass, flagged for a follow-up if wanted.
# ─────────────────────────────────────────────────────────────────

ICT_REFERENCE_TEXT = """ICT (Inner Circle Trader) reference -- the methodology SMC concepts (liquidity, order
blocks, BOS, CHoCH) originate from, going further with timing and precision-entry models.
Market structure and liquidity concepts match SMC (see SMC reference). ICT-specific additions:
Displacement -- strong impulsive candles/momentum/BOS signaling institutional activity, often
creating an FVG. Breaker Blocks -- a failed Order Block that flips role (a failed bullish OB
that price breaks below can act as resistance on return). Mitigation Blocks -- price returning
to an unfinished institutional area to fill remaining orders before continuing. PD Arrays
(Premium/Discount Arrays) -- the set of high-probability reaction zones: FVGs, Order Blocks,
Breaker Blocks, Mitigation Blocks, Rejection Blocks, Balanced Price Ranges. Optimal Trade Entry
(OTE) -- a Fibonacci pullback zone of 62-79% retracement (70.5% often emphasized) where, if
trend/liquidity/structure all align and an OB or FVG sits there too, is considered high-
probability. Dealing Range -- every swing has a low-to-high range split into discount (buy
zone), equilibrium (~50%), and premium (sell zone). Daily Bias -- today's likely direction,
distinct from raw HTF structure: built from HTF structure, the daily candle's own context,
previous day/week highs and lows, and the next liquidity target -- a wrong daily bias can
invalidate an otherwise good lower-timeframe setup. Kill Zones -- specific high-liquidity
session windows ICT emphasizes: Asian session, London Kill Zone, New York Kill Zone, London
Close; most high-quality setups cluster here. Judas Swing -- a common pattern where the session
open makes a sharp false move (e.g. London opens and price spikes down, trapping sellers) before
reversing hard the other way. SMT Divergence (Smart Money Technique) -- comparing two correlated
markets (e.g. EURUSD vs GBPUSD); if one makes a new high/low the other doesn't confirm, that
divergence can signal a reversal. Power of Three (PO3) -- the recurring intraday sequence:
Accumulation (ranging) -> Manipulation (liquidity sweep) -> Distribution (the real move).
Time -- ICT emphasizes that not every hour is equal; institutional moves cluster shortly after
London/New York opens and around major news releases. Risk management: defined stop-loss, clear
target, favorable reward:risk (2:1 commonly cited as a minimum).
ICT chart workflow: 1) HTF trend, 2) daily bias, 3) next major liquidity target, 4) mark
previous day/week highs and lows, 5) wait for a liquidity sweep, 6) look for displacement,
7) identify the FVG/OB that displacement created, 8) wait for retracement into that FVG/OB
(or the OTE zone), 9) enter on lower-timeframe confirmation, 10) target the next liquidity pool.
SMC vs ICT: SMC is the simpler subset (structure, liquidity, OBs, FVGs) -- easier for
beginners, more flexible rules. ICT is the fuller framework including all of SMC plus time,
daily bias, OTE, PO3, SMT, Judas Swing, PD Arrays, and session/kill-zone models -- steeper
learning curve, more specific execution models. Recommended learning path: 1) market structure
(HH/HL/LH/LL, BOS, CHoCH), 2) liquidity and sweeps, 3) FVGs and Order Blocks, 4) premium/
discount and dealing ranges, 5) ICT timing (daily bias, kill zones, prior day/week highs/lows),
6) advanced models (OTE, PO3, SMT divergence, Judas Swing) last."""


def run_ict_reference_publish() -> dict:
    """Live entry point: publishes the ICT deep reference to
    memory_knowledge (division=forex), separate entry from both the
    journal-sourced and SMC references."""
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=ICT_REFERENCE_TEXT,
        source="mohamed-provided-2026-07-24",
        metadata={
            "concepts": [
                "displacement",
                "breaker_blocks",
                "mitigation_blocks",
                "pd_arrays",
                "ote",
                "dealing_range",
                "daily_bias",
                "kill_zones",
                "judas_swing",
                "smt_divergence",
                "po3",
            ]
        },
    )


# ─────────────────────────────────────────────────────────────────
# Charting toolkit reference (Mohamed-provided, 2026-07-24) -- the
# practical indicator/tool set ICT/SMC traders actually use, plus the
# final, most-refined chart analysis order (supersedes the earlier,
# shorter "Practical Analysis Sequence" in the SMC reference -- kept
# both since the SMC one is still valid, just less complete).
# ─────────────────────────────────────────────────────────────────

TOOLKIT_REFERENCE_TEXT = """ICT/SMC charting toolkit reference -- a small, repeated set of tools rather than a
chart full of indicators. Essential (starred in the original): Fibonacci Retracement (for
premium/above 50%, discount/below 50%, equilibrium/50%, and the OTE 62-79% zone -- applied
after marking a clear swing high and low); Previous Day High/Low (PDH/PDL, major liquidity
targets); Previous Week High/Low (even stronger liquidity levels than daily); Session Boxes
(Asian/London/New York, since most setups cluster around London and New York opens); Economic
Calendar (checked before every trade for high-impact releases -- interest rate decisions, CPI,
NFP, FOMC, GDP -- since major news can invalidate a technical setup short-term). Manually
preferred over indicators: Market Structure (HH/HL/LH/LL, BOS, CHoCH/MSS), Fair Value Gaps
(indicators exist but many experienced traders verify manually), Order Blocks (indicators tend
to over-identify zones), Liquidity Levels (equal highs/lows, trendline liquidity, swing points).
Optional: Volume (ICT doesn't rely on it heavily, some traders use it to gauge participation
strength). Best platform: TradingView, for its Fibonacci tools, session boxes, drawing tools,
alerts, multi-timeframe support, and community indicators.
Minimal recommended chart: candlesticks only (no moving averages/oscillators) + Fibonacci
Retracement + Previous Day High/Low + Previous Week High/Low + session markers + manually-drawn
market structure + Fair Value Gaps + Order Blocks + liquidity levels + an economic calendar.
Definitive chart analysis order (most refined version, supersedes the shorter SMC sequence):
1) higher-timeframe trend (Daily/4H), 2) daily bias (bullish/bearish), 3) previous day/week
highs and lows, 4) market structure (HH/HL/LH/LL), 5) liquidity pools, 6) wait for a liquidity
sweep, 7) look for displacement, 8) mark the Order Block and/or Fair Value Gap it created,
9) use Fibonacci to find premium/discount and the OTE retracement zone, 10) enter only if
everything aligns, then target the next liquidity pool. Following this sequence consistently
turns chart-reading into a structured decision process rather than reacting emotionally to
every price move."""


def run_toolkit_reference_publish() -> dict:
    """Live entry point: publishes the charting toolkit reference to
    memory_knowledge (division=forex)."""
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=TOOLKIT_REFERENCE_TEXT,
        source="mohamed-provided-2026-07-24",
        metadata={"platform": "TradingView"},
    )


# ─────────────────────────────────────────────────────────────────
# 2026-07-25 batch: Mohamed transcribed his full handwritten forex
# notebook (42 pages, verbatim, "PAGE 1" to "PAGE 42"). Split into
# topic references rather than one giant blob, same reasoning as the
# SMC/ICT/toolkit split above -- distinct sub-topics stay independently
# queryable. News-trading content (CPI/NFP/PMI) went to news_filter.py
# instead since that's where the pause/gate logic already lives;
# personal-target numbers went to risk_management.py; the personal
# mindset list went to psychology.py. What's genuinely new here (not
# already covered by the 2026-07-24 SMC/ICT/toolkit references):
# chart-reading fundamentals, the trendline+stochastic bounce strategy,
# precise ICT kill-zone times, HTF-vs-LTF Order Block roles, Inducement
# identification detail, the Asian Range Break & Reversal strategy, the
# 200EMA+Stochastic signal, and DXY-pair correlation.
# ─────────────────────────────────────────────────────────────────

CHART_READING_REFERENCE_TEXT = """Chart-reading fundamentals reference (Mohamed's own notes, page 1-2):
Step 1 -- choose the right timeframe for your trading style: Scalping 1m-15m, Day trading
15m-1H, Swing trading 4H-Daily, Position trading Daily-Weekly.
Step 2 -- add key tools: Support & Resistance (horizontal lines at price turning points),
Trendlines (connect highs/lows to find channels or breakouts), RSI (overbought/oversold zones),
MACD (trend strength), Moving Averages EMA/SMA (trend direction), Volume (strength of moves).
Step 3 -- analyze market structure: higher-highs/higher-lows = uptrend, lower-highs/lower-lows =
downtrend; mark demand/supply zones; watch for classic chart patterns -- Head & Shoulders,
Double Top/Bottom, Flags & Pennants, Triangles.
Step 4 -- look for entry/exit signals: confluence (more than one indicator/pattern agreeing),
candlestick patterns (engulfing, pin bar, doji), breakouts or rejections from levels, and a
minimum reward:risk of 1:2.
Step 5 -- backtest: use TradingView's replay feature, step back in time, see how the analysis
would have played out, learn from both wins and mistakes before risking real trades on it."""


def run_chart_reading_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=CHART_READING_REFERENCE_TEXT,
        source="mohamed-forex-notebook-2026-07-25",
        metadata={"topic": "chart_reading_fundamentals"},
    )


TRENDLINE_REFERENCE_TEXT = """Trendline strategy reference (Mohamed's own notes, page 3-5):
Drawing trendlines: 1) identify swing points -- a swing low is where price moves down then
reverses up, a swing high is where price moves up then reverses down. 2) connect at least two
major swing points with a straight line. 3) treat trendlines as zones, not exact prices. 4) check
the line's accuracy against further price reactions.
Bounce-off-trendline strategy: in a downtrend, treat the trendline as resistance and expect
rejections; by the 3rd touch/bounce a short entry becomes valid (follow the trend, don't fade it
early). Confirmation with the Stochastic indicator: 1) wait for price to approach the trendline
zone, 2) for a downtrend, wait for the Stochastic's blue (%K) line to cross into the overbought
zone, 3) wait for %K to cross back inside the overbought zone before entering the short -- the
crossback is the confirmation, not the initial overbought touch. Risk management: stop-loss
slightly above the swing high, take-profit at 2x the stop-loss size."""


def run_trendline_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=TRENDLINE_REFERENCE_TEXT,
        source="mohamed-forex-notebook-2026-07-25",
        metadata={"topic": "trendline_stochastic_bounce"},
    )


TIME_PRICE_KILLZONE_REFERENCE_TEXT = """Time & price theory / ICT supplementary reference (Mohamed's own notes, page 6-14):
Precise kill-zone times (EST, as documented -- distinct from the broader NY-time session
windows already published in the journal-sourced strategy reference): London Open 2AM-5AM EST,
New York Open 7AM-10AM EST, London Close 11AM EST, PM session setups 1PM-4PM EST.
HTF vs LTF Order Blocks: use H4/H1/D1/W1 to find your major/HTF Order Blocks -- these are harder
to break, more accurate, and represent the strongest institutional zones, giving true direction
and the strongest POI. Use M30/M15/M5/M1 for LTF/Entry Order Blocks -- these give precise,
low-risk sniper entries, taken only as confirmation after price taps the HTF OB. Price often
returns to an OB to mitigate orders before continuing the trend.
Market Maker Model (AMD): Accumulation (consolidation before a move) -> Manipulation (stop hunts
/ liquidity grabs, false moves that trap traders) -> Distribution (price moves in the intended
direction after manipulation) -- same underlying idea as Power of Three already documented.
CRT (Counter-Trend): a temporary move against the major trend (e.g. trend is up but price
temporarily drops). Explicitly flagged as risky since it fights the dominant direction.
RTO (Return to Origin): price returning to the candle where a strong move began.
IPDA (Institutional Price Delivery Algorithm): the ICT/SMC theory describing how price is
delivered by smart money over time -- the underlying mechanism the other concepts describe.
Inducement -- how to actually identify it (distinct from an ordinary valid BOS): 1) the BOS
happens in premium, near previous highs/equal highs/session high/PDH rather than from discount
(a "real" BOS usually originates from discount). 2) the BOS is internal (breaks a minor high)
rather than external (breaking the major swing high) -- this is what invites retail breakout
buys and late trend-followers. 3) the reaction is immediate rejection: very little consolidation,
a quick push into an FVG/OB, then strong opposite displacement. Simple rule: if a BOS happens
late, in premium, near liquidity -- suspect inducement rather than trusting it as genuine
continuation.
Order Block types: Bullish OB, Bearish OB, Mitigation OB, plus Judas Swing (a false move at a
session open, most often London/NY, designed to trap traders before the real move -- already
documented) and Power of Three (already documented)."""


def run_time_price_killzone_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=TIME_PRICE_KILLZONE_REFERENCE_TEXT,
        source="mohamed-forex-notebook-2026-07-25",
        metadata={"topic": "time_price_theory_and_inducement"},
    )


ASIAN_RANGE_CHECKLIST_ITEMS: dict[str, str] = {
    "range_marked_before_midnight": "Was the Asian high/low marked using only the range formed before 12AM NY time (7/8PM-12AM window)?",
    "liquidity_swept": "Has London swept one side of the Asian range (high or low)?",
    "bos_or_choch_confirmed": "Has a BOS or CHoCH formed after the sweep?",
    "entry_from_ob_or_fvg": "Is the entry from an Order Block or Fair Value Gap formed during that structure shift?",
    "target_is_opposite_side": "Is the target the opposite side of the Asian range?",
}


@dataclass
class AsianRangeResult:
    status: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def asian_range_strategy_checklist(
    *,
    range_marked_before_midnight: bool = False,
    liquidity_swept: bool = False,
    bos_or_choch_confirmed: bool = False,
    entry_from_ob_or_fvg: bool = False,
    target_is_opposite_side: bool = False,
) -> AsianRangeResult:
    """The Asian Range Break & Reversal (London-NY kill zone) strategy,
    Mohamed's own notes page 29-31: mark the Asian high/low between
    7/8PM-12AM NY time, then wait for London to sweep one side, confirm
    a structure shift (BOS/CHoCH), enter from the OB/FVG that shift
    created, and target the opposite side of the range. Every step is
    a real precondition -- an entry taken without the sweep, or using
    Asian-range levels updated after midnight, is exactly the mistake
    the notes explicitly warn against (updating the range after 12AM,
    using the full Asian session instead of the pre-midnight range, or
    entering before the sweep/structure shift actually happens)."""
    passed: list[str] = []
    failed: list[str] = []
    notes: list[str] = []

    for key, ok in [
        ("range_marked_before_midnight", range_marked_before_midnight),
        ("liquidity_swept", liquidity_swept),
        ("bos_or_choch_confirmed", bos_or_choch_confirmed),
        ("entry_from_ob_or_fvg", entry_from_ob_or_fvg),
        ("target_is_opposite_side", target_is_opposite_side),
    ]:
        (passed if ok else failed).append(key)
        if not ok:
            notes.append(f"{ASIAN_RANGE_CHECKLIST_ITEMS[key]} -- not confirmed.")

    if not range_marked_before_midnight:
        status = STATUS_REJECTED
        notes.append(
            "Without a range marked before 12AM NY, this isn't the documented strategy at all -- reject outright rather than treat as merely pending."
        )
    elif not liquidity_swept or not bos_or_choch_confirmed:
        status = STATUS_REJECTED
        notes.append(
            "Entering before the sweep and structure shift are confirmed is exactly the mistake the notes warn against."
        )
    elif failed:
        status = STATUS_PENDING
    else:
        status = STATUS_VALIDATED
        notes.append("All 5 Asian Range Break & Reversal checklist items confirmed.")

    return AsianRangeResult(status=status, passed=passed, failed=failed, notes=notes)


def ema_stochastic_signal(
    price_above_200ema: bool | None,
    stochastic_zone: str | None,  # "oversold" | "overbought" | "neutral" | None
    crossed_back: bool = False,
) -> dict:
    """The 200EMA + Stochastic strategy, Mohamed's own notes page 31-32.
    Trend filter: price above the 200EMA -> only look for buys; price
    below -> only look for sells. Signal: Stochastic must reach the
    zone matching that bias (oversold for a buy, overbought for a
    sell) AND cross back inside before entering -- the notes are
    explicit that reaching overbought/oversold alone is not enough,
    you wait for the cross-back confirmation. Returns direction=None
    with a note whenever any precondition isn't met, never guesses."""
    if price_above_200ema is None or stochastic_zone is None:
        return {"direction": None, "notes": ["200EMA position and/or Stochastic zone not given -- can't evaluate."]}

    if price_above_200ema and stochastic_zone == "oversold" and crossed_back:
        return {
            "direction": "buy",
            "notes": [
                "Price above 200EMA (uptrend bias) + Stochastic oversold with confirmed cross-back inside -- buy signal per the documented rule."
            ],
        }
    if not price_above_200ema and stochastic_zone == "overbought" and crossed_back:
        return {
            "direction": "sell",
            "notes": [
                "Price below 200EMA (downtrend bias) + Stochastic overbought with confirmed cross-back inside -- sell signal per the documented rule."
            ],
        }

    if not crossed_back and stochastic_zone in ("oversold", "overbought"):
        return {
            "direction": None,
            "notes": [
                f"Stochastic is in the {stochastic_zone} zone but hasn't crossed back inside yet -- the notes are explicit this isn't a signal on its own, wait for the cross-back."
            ],
        }

    return {
        "direction": None,
        "notes": [
            "200EMA trend bias and Stochastic zone don't line up for a signal (e.g. uptrend bias with an overbought reading, not oversold)."
        ],
    }


DXY_PAIR_CORRELATION: dict[str, dict[str, str]] = {
    # Direction DXY implies for each pair Mohamed trades, per his own notes (page 37-38).
    # EURUSD/GBPUSD/USDJPY are the 3 explicitly named in his notes -- USDJPY was actually
    # missing from this table until 2026-07-26 despite being documented as named, a real
    # gap fixed alongside the pair-list expansion. USDCAD/XAUUSD/USDCHF/AUDUSD are extended
    # here via the same USD-is-base-or-quote logic but flagged as inferred, not directly
    # documented, so that distinction isn't silently lost.
    "EURUSD": {"bullish": "sell", "bearish": "buy"},
    "GBPUSD": {"bullish": "sell", "bearish": "buy"},
    "USDJPY": {"bullish": "buy", "bearish": "sell"},
    "USDCAD": {"bullish": "buy", "bearish": "sell"},
    "USDCHF": {"bullish": "buy", "bearish": "sell"},
    "AUDUSD": {"bullish": "sell", "bearish": "buy"},
    "XAUUSD": {"bullish": "sell", "bearish": "buy"},
}
DXY_INFERRED_PAIRS = {"USDCAD", "XAUUSD", "USDCHF", "AUDUSD"}


TRADING_SCHEDULE_REFERENCE_TEXT = """Trading schedule reference, Mohamed's own explicit correction (2026-07-26):
Traded pairs (8 total): EURUSD, GBPUSD, USDCAD, USDJPY, USDCHF, AUDUSD, NAS100 trade all 5
weekdays; XAUUSD trades only Tuesday/Wednesday/Thursday. This is a WATCHLIST, not a mandate --
being eligible on a given day does not mean that pair must be traded that day. The actual rule
is opportunistic: only take a trade when a real setup appears on one of these pairs.
Priority tier ("more eyes"): EURUSD, USDJPY, XAUUSD, USDCAD, USDCHF, and NAS100 get extra
attention. GBPUSD and AUDUSD are tradeable but not in this priority tier.
DXY (US Dollar Index) is checked every single day as context -- it is never itself traded, but
its direction helps confirm or contradict a proposed trade on the USD-related pairs above (see
dxy_bias_check())."""


def run_trading_schedule_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=TRADING_SCHEDULE_REFERENCE_TEXT,
        source="mohamed-provided-2026-07-26",
        metadata={"traded_pairs": sorted(TRADED_PAIRS), "priority_pairs": sorted(PRIORITY_PAIRS)},
    )


def dxy_bias_check(dxy_direction: str, pair: str, proposed_direction: str) -> dict:
    """DXY bias/liquidity-clue check, Mohamed's own notes page 37-38:
    most of his traded pairs are USD-related, so DXY direction should
    agree with a proposed trade direction -- "if your pair setup fights
    DXY, probability drops." Only EURUSD/GBPUSD/USDJPY are explicitly
    named in the notes; USDCAD/XAUUSD/USDCHF/AUDUSD are extended here
    via the same USD-is-base-or-quote logic and explicitly flagged as
    inferred rather than directly documented, so that distinction isn't
    silently lost."""
    pair_upper = pair.upper()
    expected = DXY_PAIR_CORRELATION.get(pair_upper, {}).get(dxy_direction)
    if expected is None:
        return {
            "alignment": "unknown_pair",
            "notes": [f"{pair_upper} isn't in the documented/inferred DXY correlation table."],
        }

    inferred_note = (
        " (inferred from USD-is-base logic, not directly named in the notes)"
        if pair_upper in DXY_INFERRED_PAIRS
        else ""
    )
    if proposed_direction == expected:
        return {
            "alignment": "aligned",
            "notes": [
                f"DXY {dxy_direction} implies {expected} on {pair_upper}{inferred_note} -- proposed direction agrees."
            ],
        }
    return {
        "alignment": "fights_dxy",
        "notes": [
            f"DXY {dxy_direction} implies {expected} on {pair_upper}{inferred_note}, but proposed direction is {proposed_direction} -- 'if your pair setup fights DXY, probability drops.'"
        ],
    }


# ─────────────────────────────────────────────────────────────────
# 2026-07-25 (later same day): "First Candle Rule" -- a separate
# strategy Mohamed described verbally (opening-range break confirmed
# by a Fair Value Gap), which he says made him over $1,000 in a single
# month using only this one setup. Distinct from the Asian Range
# strategy above -- that one is session-liquidity-based (Asian range,
# London sweep); this one is anchored to the 9:30-9:35 AM NY cash-
# market open, which fits NAS100 specifically among currently traded
# pairs (EURUSD/GBPUSD/USDCAD/XAUUSD don't have an equivalent NYSE-open
# opening range). The dictated reward:risk ("six six two to one") was
# ambiguous in transcription -- confirmed directly with Mohamed as 1:2,
# not guessed, since this is a real number that decides position
# sizing. Kept as its own minimum (MOHAMED_FIRST_CANDLE_MIN_REWARD_TO_RISK)
# rather than reusing MOHAMED_MIN_REWARD_TO_RISK (3.0), since he
# described this as a separate, faster strategy with its own economics.
# ─────────────────────────────────────────────────────────────────

MOHAMED_FIRST_CANDLE_MIN_REWARD_TO_RISK = 2.0

FIRST_CANDLE_RULE_CHECKLIST_ITEMS: dict[str, str] = {
    "opening_range_marked": "Was the 9:30-9:35 AM NY opening candle's high/low marked?",
    "range_broken": "Has price broken above or below that opening range on the 1-minute chart?",
    "fvg_confirms_break": "Did a Fair Value Gap form confirming the break -- not just a candle close, and not just a wick?",
    "reward_to_risk_ok": "Does the trade offer at least 1:2 reward:risk?",
}


@dataclass
class FirstCandleRuleResult:
    status: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def first_candle_rule_checklist(
    *,
    opening_range_marked: bool = False,
    range_broken: bool = False,
    fvg_confirms_break: bool = False,
    reward_to_risk: float | None = None,
) -> FirstCandleRuleResult:
    """The First Candle Rule, Mohamed-provided 2026-07-25: mark the
    high/low of the 9:30-9:35 AM NY opening candle, drop to the
    1-minute chart, and wait for a break confirmed specifically by a
    Fair Value Gap -- a plain candle close or a wick alone doesn't
    count, since the FVG is what shows genuine institutional
    participation behind the move ("the big dollars pushing the
    market"). Stop-loss goes at the first candle that closed outside
    the range; the FVG doesn't need to be retested before entering
    since price tends to run quickly once it forms."""
    passed: list[str] = []
    failed: list[str] = []
    notes: list[str] = []

    if not opening_range_marked:
        failed.append("opening_range_marked")
        notes.append("Opening range (9:30-9:35 AM NY candle) not marked -- nothing to break yet.")
    else:
        passed.append("opening_range_marked")

    if not range_broken:
        failed.append("range_broken")
        notes.append("Price hasn't broken the opening range yet.")
    else:
        passed.append("range_broken")

    if not fvg_confirms_break:
        failed.append("fvg_confirms_break")
        notes.append(
            "Break not yet confirmed by a Fair Value Gap -- a candle close or wick alone isn't enough per this strategy's own rule."
        )
    else:
        passed.append("fvg_confirms_break")

    if reward_to_risk is not None and reward_to_risk >= MOHAMED_FIRST_CANDLE_MIN_REWARD_TO_RISK:
        passed.append("reward_to_risk_ok")
    else:
        failed.append("reward_to_risk_ok")
        notes.append(
            f"Reward:risk is {reward_to_risk if reward_to_risk is not None else 'not given'} -- this strategy's confirmed minimum is {MOHAMED_FIRST_CANDLE_MIN_REWARD_TO_RISK:.0f}:1."
        )

    if not opening_range_marked or not range_broken:
        status = STATUS_REJECTED
    elif not fvg_confirms_break:
        status = STATUS_REJECTED
        notes.append(
            "Entering without FVG confirmation is exactly the mistake this strategy warns against -- reject, don't just flag pending."
        )
    elif failed:
        status = STATUS_PENDING
    else:
        status = STATUS_VALIDATED
        notes.append("All First Candle Rule checklist items confirmed.")

    return FirstCandleRuleResult(status=status, passed=passed, failed=failed, notes=notes)


FIRST_CANDLE_RULE_REFERENCE_TEXT = """First Candle Rule (opening range break + FVG confirmation), Mohamed's own strategy,
reported to have made him over $1,000 in a single month using only this one setup: 1) mark the
high and low of the opening candle that forms between 9:30-9:35 AM (NY cash-market open -- most
relevant to NAS100 among currently traded pairs). 2) drop to the 1-minute chart and wait for a
break of that range. 3) confirm the break specifically with a Fair Value Gap -- not a candle
close alone, and not just a wick; the FVG is what shows genuine institutional ("big dollar")
participation pushing the market, and the goal is to be on the same side as that flow. 4) enter
once the FVG confirms. 5) stop-loss at the first candle that closed outside the range. 6) no need
to wait for price to retrace into the FVG before entering -- it tends to run quickly once
confirmed. 7) target: minimum 1:2 reward:risk (confirmed directly 2026-07-25 after an ambiguous
dictation -- distinct from the SMC checklist's stricter personal 3:1 minimum, since this is a
separate, faster strategy with its own economics). Mohamed's own framing: "stupid simple always
wins" after 9 years in the markets."""


def run_first_candle_rule_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=FIRST_CANDLE_RULE_REFERENCE_TEXT,
        source="mohamed-provided-2026-07-25",
        metadata={
            "checklist_items": list(FIRST_CANDLE_RULE_CHECKLIST_ITEMS.keys()),
            "min_reward_to_risk": MOHAMED_FIRST_CANDLE_MIN_REWARD_TO_RISK,
        },
    )


# ─────────────────────────────────────────────────────────────────
# 2026-07-25 (later still): Daily Bias / ICT 2022 Model liquidity-
# sweep strategy -- Mohamed describes this as the single strategy that
# made him a profitable trader ($40,000 in a month, by his own
# account), anchored to one timeframe and roughly the same time each
# day. Unlike the First Candle Rule and the SMC checklist, no fixed
# reward:risk was given for this one -- deliberately left ungated
# rather than inventing a number for a real financial decision.
# ─────────────────────────────────────────────────────────────────

DAILY_BIAS_LEVELS = ["previous_day_high", "previous_day_low", "asia_high", "asia_low", "london_high", "london_low"]


@dataclass
class DailyBiasSweepResult:
    scenario: str  # "reversal" | "failed_reversal_continuation" | "no_setup"
    status: str
    notes: list[str] = field(default_factory=list)


def daily_bias_ict2022_checklist(
    *,
    level_swept: str | None = None,
    after_930_ny_open: bool = False,
    displacement_fvg_formed: bool = False,
    retracement_into_fvg: bool = False,
    reversal_then_invalidated: bool = False,
) -> DailyBiasSweepResult:
    """Mohamed's own daily-bias liquidity strategy (2026-07-25): mark
    yesterday's high/low plus the Asian and London session highs/lows
    (6 levels total) each day; after the 9:30 AM NY open one of these
    levels typically gets swept. Two valid setups from there: 1) the
    ICT 2022 Model reversal -- sweep, then displacement/FVG opposite
    the sweep direction, then a retracement into that FVG, then
    continuation toward the opposite liquidity target. 2) his own
    emphasized case -- a failed-reversal continuation, where the
    reversal attempt above gets invalidated (price breaks back through
    the FVG/structure in the ORIGINAL sweep direction). He credits
    this second case, not the first, as what actually made him
    profitable and calls it "the most explosive" of the two -- so it's
    modeled here as a distinct valid scenario, not a failed setup."""
    notes: list[str] = []

    if not level_swept or level_swept not in DAILY_BIAS_LEVELS:
        return DailyBiasSweepResult(
            scenario="no_setup",
            status=STATUS_REJECTED,
            notes=["No recognized level swept yet (previous day high/low, Asia high/low, London high/low)."],
        )

    if not after_930_ny_open:
        notes.append("Documented timing is after the 9:30 AM NY open -- this sweep is outside that window.")

    if not displacement_fvg_formed:
        return DailyBiasSweepResult(
            scenario="no_setup",
            status=STATUS_PENDING,
            notes=notes + [f"{level_swept} swept but no displacement/FVG confirming a reaction yet."],
        )

    if reversal_then_invalidated:
        notes.append(
            f"{level_swept} swept, reversal attempt formed, then invalidated back through in the original sweep direction -- per Mohamed's own rule, this failed-reversal case is the most explosive continuation setup, not a failure to trade."
        )
        return DailyBiasSweepResult(scenario="failed_reversal_continuation", status=STATUS_VALIDATED, notes=notes)

    if retracement_into_fvg:
        notes.append(
            f"{level_swept} swept, displacement/FVG formed opposite the sweep direction, retracement into the FVG confirmed -- ICT 2022 Model reversal setup, target the opposite liquidity level."
        )
        return DailyBiasSweepResult(scenario="reversal", status=STATUS_VALIDATED, notes=notes)

    notes.append(
        "Displacement/FVG formed but retracement into it not yet confirmed -- wait before entering the reversal leg."
    )
    return DailyBiasSweepResult(scenario="reversal", status=STATUS_PENDING, notes=notes)


DAILY_BIAS_ICT2022_REFERENCE_TEXT = """Daily Bias / ICT 2022 Model liquidity-sweep strategy, Mohamed's own strategy
(reported as the single approach that made him a profitable trader, describing a $40,000 month
using only this one setup on one timeframe, occurring at roughly the same time each day):
1) Each day, mark 6 key levels: yesterday's high and low (Previous Day High/Low), plus the
Asian session's high and low and the London session's high and low. 2) After the 9:30 AM NY
open, one of these levels typically gets hit/swept. 3) Once swept, look for one of two outcomes:
   a) ICT 2022 Model reversal -- the easier, more commonly taught case: liquidity sweep, then a
   displacement move (creating a Fair Value Gap) in the opposite direction, then a retracement
   into that FVG, then continuation toward the opposite liquidity target.
   b) Failed-reversal continuation -- Mohamed's own emphasized case, and what he credits with
   making him profitable: when the reversal attempt above fails (price breaks back through the
   FVG/structure in the ORIGINAL sweep direction instead of holding the reversal), this signals a
   stop-run/continuation move in the original direction -- described as producing the most
   explosive trades of the two scenarios, not a failed setup to avoid.
No fixed reward:risk was given for this strategy (distinct from the First Candle Rule's confirmed
1:2 and the SMC checklist's personal 3:1 minimum) -- left ungated in the checklist function rather
than inventing a number."""


def run_daily_bias_ict2022_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-strategy-v0.1",
        content=DAILY_BIAS_ICT2022_REFERENCE_TEXT,
        source="mohamed-provided-2026-07-25",
        metadata={"levels": DAILY_BIAS_LEVELS},
    )
