"""Market Analytics Agent v0.1 -- Forex Division.

Pulls real-time OHLC candle data directly from a locally-running MT5
terminal via the official MetaTrader5 Python package -- see
CONTEXT.md for the full reasoning behind choosing this over every
third-party data source considered (Finnhub/Massive-Polygon: free
tiers are 15-20 min delayed; TradingView: no public API at all, only
unofficial scrapers/desktop-automation MCP servers). MT5 is free,
genuinely real-time, and matches the exact prices Mohamed would
actually trade at, since it's his broker's own feed, not a third-party
approximation.

Split deliberately into two layers:
  - connect()/fetch_candles(): need a real, running, logged-in MT5
    terminal -- can't be unit-tested without one.
  - classify_structure(): pure swing-high/swing-low + trend logic,
    fully testable against synthetic candle data regardless of whether
    MT5 is connected. This is what feeds Strategy Agent's
    structure_identified / htf_trend checklist inputs once wired up.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from agents.forex._pairs import TRADED_PAIRS

# String timeframe names -> MT5's own constants, resolved lazily (only
# when MetaTrader5 is actually imported/used) so this module can be
# imported and unit-tested even on a machine without MT5 installed.
_TIMEFRAME_NAMES = ["W1", "D1", "H4", "H1", "M15", "M5"]

TrendLabel = Literal["uptrend", "downtrend", "ranging", "unknown"]


@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class SwingPoint:
    index: int
    price: float
    kind: str  # "high" | "low"


@dataclass
class StructureResult:
    trend: TrendLabel
    swings: list[SwingPoint] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _get_mt5_timeframe(name: str):
    import MetaTrader5 as mt5

    mapping = {
        "W1": mt5.TIMEFRAME_W1,
        "D1": mt5.TIMEFRAME_D1,
        "H4": mt5.TIMEFRAME_H4,
        "H1": mt5.TIMEFRAME_H1,
        "M15": mt5.TIMEFRAME_M15,
        "M5": mt5.TIMEFRAME_M5,
    }
    if name not in mapping:
        raise ValueError(f"Unknown timeframe '{name}'. Allowed: {_TIMEFRAME_NAMES}")
    return mapping[name]


def connect() -> bool:
    """Initializes the connection to whatever MT5 terminal is
    currently running and logged in on this machine. Returns False
    (never raises) if no terminal is found -- callers check the return
    value rather than catching an exception."""
    import MetaTrader5 as mt5

    return mt5.initialize()


def disconnect() -> None:
    import MetaTrader5 as mt5

    mt5.shutdown()


# Some brokers name an instrument entirely differently, not just with
# a suffix (e.g. Exness lists the Nasdaq 100 as USTEC, not NAS100).
# Suffix variants (EURUSD -> EURUSDm) are handled generically by
# resolve_symbol()'s prefix search below -- this dict is only for
# names that don't share a common prefix at all.
_SYMBOL_NAME_ALIASES: dict[str, list[str]] = {
    "NAS100": ["USTEC", "NDX100", "US100"],
    "DXY": ["USDX", "DX", "USDOLLAR"],
}

# DXY isn't traded (no entry/exit decisions made on it directly) -- it's
# checked daily as context for the other pairs (Mohamed's own explicit
# instruction, 2026-07-26), same spirit as dxy_bias_check() in
# strategy.py. Kept separate from TRADED_PAIRS since it's never itself
# a trade candidate.
DXY_SYMBOL = "DXY"

_symbol_cache: dict[str, str] = {}


def resolve_symbol(clean_pair: str) -> str:
    """MT5 symbol names vary by broker -- Exness suffixes everything
    with 'm' (EURUSD -> EURUSDm) and names the Nasdaq 100 USTEC, not
    NAS100. Rather than hardcoding one broker's convention, this finds
    the best-matching actual symbol on whatever terminal is connected.
    Cached per process since the broker's symbol list doesn't change
    mid-session."""
    if clean_pair in _symbol_cache:
        return _symbol_cache[clean_pair]

    import MetaTrader5 as mt5

    if mt5.symbol_info(clean_pair) is not None:
        _symbol_cache[clean_pair] = clean_pair
        return clean_pair

    candidates = [clean_pair] + _SYMBOL_NAME_ALIASES.get(clean_pair, [])
    all_names = [s.name for s in mt5.symbols_get()]

    for candidate in candidates:
        matches = [n for n in all_names if n.upper().startswith(candidate.upper())]
        if matches:
            resolved = min(matches, key=len)  # prefer the plainest variant over extended ones like _x100m
            _symbol_cache[clean_pair] = resolved
            return resolved

    raise ValueError(f"No matching MT5 symbol found for '{clean_pair}' on this broker's symbol list.")


def fetch_candles(symbol: str, timeframe: str, count: int = 200) -> list[Candle]:
    """Pulls the most recent `count` closed candles for symbol/
    timeframe from the connected terminal. `symbol` is the clean pair
    name (e.g. "EURUSD", "NAS100") -- resolved internally to whatever
    this broker actually calls it via resolve_symbol(), so callers
    (and other agents referencing TRADED_PAIRS) never need to know
    broker-specific naming. Caller must call connect() first (and
    check it returned True) -- this doesn't auto-connect, so a caller
    doing multiple fetches isn't re-initializing every time."""
    import MetaTrader5 as mt5

    resolved_symbol = resolve_symbol(symbol)
    tf = _get_mt5_timeframe(timeframe)
    rates = mt5.copy_rates_from_pos(resolved_symbol, tf, 0, count)
    if rates is None:
        raise RuntimeError(
            f"copy_rates_from_pos returned None for {resolved_symbol} (resolved from {symbol})/{timeframe}: {mt5.last_error()}"
        )

    return [
        Candle(
            time=datetime.fromtimestamp(r["time"], tz=UTC),
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            volume=int(r["tick_volume"]),
        )
        for r in rates
    ]


def _dedupe_adjacent_swings(swings: list[SwingPoint]) -> list[SwingPoint]:
    """Overlapping sliding windows can flag two or more consecutive
    candles as the same swing (a near-flat top/bottom ties across
    adjacent windows) -- collapse consecutive same-kind entries down
    to the single most extreme one, so a real turning point isn't
    double-counted as two separate, near-identical swings (which was
    a real bug: comparing two duplicate points with strict > always
    evaluates as "not rising," even inside a genuine uptrend)."""
    if not swings:
        return []
    deduped = [swings[0]]
    for s in swings[1:]:
        last = deduped[-1]
        if s.kind == last.kind:
            is_more_extreme = (s.kind == "high" and s.price >= last.price) or (
                s.kind == "low" and s.price <= last.price
            )
            if is_more_extreme:
                deduped[-1] = s
        else:
            deduped.append(s)
    return deduped


def classify_structure(candles: list[Candle], swing_lookback: int = 5) -> StructureResult:
    """Pure logic, no MT5 dependency -- fully unit-testable. A candle
    at index i is a swing high if its high is the highest among the
    swing_lookback candles on either side (swing low, symmetric on
    lows). Classifies the trend from the two most recent swing highs
    and two most recent swing lows: both rising = uptrend (HH/HL),
    both falling = downtrend (LH/LL), mixed = ranging."""
    if len(candles) < swing_lookback * 2 + 1:
        return StructureResult(
            trend="unknown", notes=[f"Need at least {swing_lookback * 2 + 1} candles, got {len(candles)}."]
        )

    raw_swings: list[SwingPoint] = []
    for i in range(swing_lookback, len(candles) - swing_lookback):
        window = candles[i - swing_lookback : i + swing_lookback + 1]
        if candles[i].high == max(c.high for c in window):
            raw_swings.append(SwingPoint(index=i, price=candles[i].high, kind="high"))
        elif candles[i].low == min(c.low for c in window):
            raw_swings.append(SwingPoint(index=i, price=candles[i].low, kind="low"))

    swings = _dedupe_adjacent_swings(raw_swings)
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    notes: list[str] = []
    if len(highs) < 2 or len(lows) < 2:
        return StructureResult(
            trend="unknown", swings=swings, notes=["Not enough swing highs/lows identified yet to classify a trend."]
        )

    # Three-way comparison, not a boolean -- equal (flat) values are
    # neither rising nor falling, and treating "not rising" as
    # equivalent to "falling" was a real bug: flat/ranging price
    # action was being misclassified as a downtrend.
    rising_highs = highs[-1].price > highs[-2].price
    falling_highs = highs[-1].price < highs[-2].price
    rising_lows = lows[-1].price > lows[-2].price
    falling_lows = lows[-1].price < lows[-2].price

    if rising_highs and rising_lows:
        trend: TrendLabel = "uptrend"
        notes.append("Higher highs and higher lows (HH/HL) -- uptrend.")
    elif falling_highs and falling_lows:
        trend = "downtrend"
        notes.append("Lower highs and lower lows (LH/LL) -- downtrend.")
    else:
        trend = "ranging"
        notes.append("Highs and lows disagree on direction -- ranging/unclear structure.")

    return StructureResult(trend=trend, swings=swings, notes=notes)


def run_market_analytics_sweep(
    pairs: set[str] | None = None, timeframe: str = "H4", count: int = 200
) -> dict[str, StructureResult]:
    """Live entry point: connects to MT5, pulls candles for every
    traded pair on the given timeframe plus DXY (context only, never a
    trade candidate -- Mohamed's own instruction, 2026-07-26, checked
    daily since it helps read the other pairs), classifies structure,
    logs a combined report to memory_knowledge. Returns {} (never
    raises) if MT5 isn't reachable -- same fail-safe pattern as the
    other agents, a down data source shouldn't crash the sweep.

    Catches both RuntimeError (fetch_candles' own raise when MT5
    returns no data) and ValueError (resolve_symbol's raise when a
    broker simply doesn't list that symbol at all) -- the original code
    only caught RuntimeError, which would have let an unresolvable
    symbol crash the entire sweep instead of just skipping that one
    instrument. Real risk for DXY specifically: not every broker lists
    it (Exness, Mohamed's demo broker, was previously confirmed to have
    no crypto symbols at all -- DXY/USDX availability isn't guaranteed
    either), so this needed to degrade gracefully, not just for DXY but
    for any future pair too."""
    from agents.forex._memory_helpers import safe_add_knowledge

    pairs = pairs or TRADED_PAIRS

    if not connect():
        return {}

    results: dict[str, StructureResult] = {}
    dxy_result: StructureResult | None = None
    try:
        for pair in pairs:
            try:
                candles = fetch_candles(pair, timeframe, count)
                results[pair] = classify_structure(candles)
            except (RuntimeError, ValueError):
                continue

        try:
            dxy_candles = fetch_candles(DXY_SYMBOL, timeframe, count)
            dxy_result = classify_structure(dxy_candles)
        except (RuntimeError, ValueError):
            dxy_result = None
    finally:
        disconnect()

    if results or dxy_result:
        lines = [f"{pair}: {r.trend} ({'; '.join(r.notes)})" for pair, r in results.items()]
        if dxy_result:
            lines.append(f"DXY (context only, not traded): {dxy_result.trend} ({'; '.join(dxy_result.notes)})")
        summary = "\n".join(lines)
        safe_add_knowledge(
            division="forex",
            agent_id="forex-market-analytics-v0.1",
            content=f"Market structure sweep ({timeframe}):\n{summary}",
            source="MT5",
            metadata={"timeframe": timeframe, "pairs": list(results.keys()), "dxy_included": dxy_result is not None},
        )

    return results
