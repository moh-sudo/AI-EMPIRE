"""News Filter Agent v0.1 -- Forex Division.

Distinct from the Research Agent: Research compiles broad market
reports (calendar + central bank statements, published as reference
knowledge). News Filter's job is narrower and time-sensitive --
"is there high-impact news imminent enough that I should NOT be
entering a trade on this pair right now" -- directly implementing the
journal's own rule: "should not trade on news session unless its less
volatile." Reuses Research's fetch/parse logic rather than duplicating
it; this agent adds the urgency window and the pair-level gate check.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

import requests

from agents.forex.research import CalendarEvent, fetch_forexfactory_calendar

# Maps traded pairs to the currencies whose news could move them.
# Expanded 2026-07-26 alongside the pair-list expansion in agents/forex/_pairs.py.
PAIR_CURRENCIES = {
    "EURUSD": {"EUR", "USD"},
    "GBPUSD": {"GBP", "USD"},
    "USDCAD": {"USD", "CAD"},
    "USDJPY": {"USD", "JPY"},
    "USDCHF": {"USD", "CHF"},
    "AUDUSD": {"AUD", "USD"},
    "XAUUSD": {"USD"},  # gold trades primarily off USD/risk-sentiment news
    "NAS100": {"USD"},
}

DEFAULT_WINDOW_MINUTES = 30
ALERT_IMPACT_LEVELS = {"Medium", "High"}


@dataclass
class NewsGateResult:
    pair: str
    should_pause: bool
    imminent_events: list[CalendarEvent] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    data_unavailable: bool = False  # True means "couldn't verify", not "confirmed clear"


def _is_imminent(event: CalendarEvent, now: datetime, within_minutes: int) -> bool:
    if event.date is None:
        return False
    delta = (event.date - now).total_seconds() / 60
    return 0 <= delta <= within_minutes


def should_pause_for_news(
    pair: str,
    within_minutes: int = DEFAULT_WINDOW_MINUTES,
    events: list[CalendarEvent] | None = None,
) -> NewsGateResult:
    """The actual gate check -- callable by Entry & Exit or the
    CEO/Lead agent before a trade proceeds. events param lets callers
    pass an already-fetched calendar to avoid refetching per pair.

    Fails closed, not open: if the calendar can't be fetched, this
    returns should_pause=True with data_unavailable=True -- "couldn't
    verify" is never silently treated as "confirmed clear" for a gate
    that a real trading decision depends on. Callers can inspect
    data_unavailable to distinguish a real detected event from an
    unknown-state caution."""
    pair_upper = pair.upper()
    currencies = PAIR_CURRENCIES.get(pair_upper, set())
    now = datetime.now(UTC)

    if events is None:
        try:
            events = fetch_forexfactory_calendar()
        except requests.RequestException:
            return NewsGateResult(pair=pair_upper, should_pause=True, checked_at=now, data_unavailable=True)

    imminent = [
        e
        for e in events
        if e.country in currencies and e.impact in ALERT_IMPACT_LEVELS and _is_imminent(e, now, within_minutes)
    ]

    return NewsGateResult(pair=pair_upper, should_pause=bool(imminent), imminent_events=imminent, checked_at=now)


def build_news_alert(result: NewsGateResult) -> str:
    if result.data_unavailable:
        return f"{result.pair}: PAUSE -- news calendar unavailable, can't verify there's no imminent high-impact event."
    if not result.should_pause:
        return f"{result.pair}: no high-impact news in the next {DEFAULT_WINDOW_MINUTES} minutes."
    lines = [f"{result.pair}: PAUSE -- high-impact news imminent:"]
    for e in result.imminent_events:
        when = e.date.strftime("%H:%M UTC") if e.date else "time unknown"
        lines.append(f"  [{e.impact}] {e.country} {e.title} at {when}")
    return "\n".join(lines)


def run_news_check_sweep(within_minutes: int = DEFAULT_WINDOW_MINUTES) -> list[NewsGateResult]:
    """Live entry point: checks every traded pair once, using a single
    shared calendar fetch (not one per pair). Logs a memory_experience
    entry for any pair that needs a pause, including the data-
    unavailable case -- that's a real finding worth a record, not
    something to silently swallow."""
    from agents.forex._memory_helpers import safe_add_experience

    try:
        events = fetch_forexfactory_calendar()
        fetch_failed = False
    except requests.RequestException:
        events = []
        fetch_failed = True

    now = datetime.now(UTC)
    if fetch_failed:
        results = [
            NewsGateResult(pair=p, should_pause=True, checked_at=now, data_unavailable=True) for p in PAIR_CURRENCIES
        ]
    else:
        results = [should_pause_for_news(pair, within_minutes, events=events) for pair in PAIR_CURRENCIES]

    for result in results:
        if result.should_pause:
            safe_add_experience(
                division="forex",
                agent_id="forex-news-filter-v0.1",
                event_type="news_pause_alert",
                context=build_news_alert(result),
                outcome="data_unavailable" if result.data_unavailable else "pause",
                metadata={
                    "pair": result.pair,
                    "event_count": len(result.imminent_events),
                    "checked_at": result.checked_at.isoformat(),
                    "data_unavailable": result.data_unavailable,
                },
            )

    return results


# ─────────────────────────────────────────────────────────────────
# 2026-07-25: news-trading reference + indicator-surprise interpreter,
# from Mohamed's transcribed handwritten notebook (pages 17-28). This
# is deliberately kept in News Filter rather than Research -- Research
# publishes broad market reports, News Filter is specifically about
# "should I act on this news right now," which is exactly what these
# pages cover (CPI/NFP/ISM PMI direction rules, and the post-release
# waiting rule the pre-event should_pause_for_news() gate above doesn't
# address at all -- that gate only covers *before* release).
# ─────────────────────────────────────────────────────────────────

NEWS_TRADING_REFERENCE_TEXT = """News-trading reference (Mohamed's own notes, page 17-28):
ISM Services PMI (Institute for Supply Management, services sector ~70-80% of the US economy):
above 50 = expanding/good for USD, below 50 = contracting/bad for USD, exactly 50 = no
growth/no decline. Strong-and-above-forecast PMI -> USD strengthens -> XAUUSD/Gold falls,
indices can rise (strong economy expected). Weak-and-below-forecast PMI -> USD weakens ->
XAUUSD rises, indices can drop (recession fear).
Non-Farm Payrolls (NFP, monthly, first week, extremely volatile -- can move XAUUSD 100-500
pips): high/above-forecast NFP -> stronger USD -> XAUUSD down; low/below-forecast -> weaker
USD -> XAUUSD up. The 3 NFP numbers, in order of importance: 1) Non-farm Employment Change
(jobs added/lost -- very high impact), 2) Average Hourly Earnings/wages (very high impact, since
higher wages -> more spending -> higher inflation -> stronger USD expectations), 3) Unemployment
Rate (high impact but slower-reacting than the jobs number). Also watch weekly Unemployment
Claims (released every Thursday): more claims -> more job losses -> USD weakness; fewer claims
-> USD strength.
CPI (Consumer Price Index, monthly): the most explosive release after NFP since it directly
tells the Fed whether inflation is rising or falling, which drives interest-rate expectations.
Core CPI (excludes food & energy, more stable) is what actually moves the market -- always check
Core CPI first. High Core CPI -> USD pumps (rate-hike expectations); low Core CPI -> USD pumps
in the other direction (rate-cut expectations, i.e. still USD strength expectations shift, watch
direction carefully against forecast).
Universal post-release rule (applies to all of the above): 1) wait 2-5 minutes after the release
-- the first 1-5 minutes are typically a fake move / stop-hunt as market makers grab liquidity,
not the real direction. 2) wait for the first 1-minute or 5-minute candle to close -- if it's a
huge candle, wait for a pullback rather than chasing it. 3) look for real structure confirmation
after the news candle (a genuine BOS/CHoCH, return to a supply/demand zone, a clean FVG/imbalance,
then a retest) before entering on the pullback, not the initial spike. If results are mixed, the
first spike is fake and the true move comes after ~5 minutes."""


def run_news_trading_reference_publish() -> dict:
    from agents.forex._memory_helpers import safe_add_knowledge

    return safe_add_knowledge(
        division="forex",
        agent_id="forex-news-filter-v0.1",
        content=NEWS_TRADING_REFERENCE_TEXT,
        source="mohamed-forex-notebook-2026-07-25",
        metadata={"topic": "news_trading_cpi_nfp_pmi"},
    )


IndicatorName = Literal[
    "ism_services_pmi",
    "nfp_employment_change",
    "cpi_core",
    "unemployment_rate",
    "unemployment_claims",
    "avg_hourly_earnings",
]

# direction: "beat" (better for USD) / "miss" (worse for USD) / "inline"
_HIGHER_IS_USD_BULLISH = {"ism_services_pmi", "nfp_employment_change", "cpi_core", "avg_hourly_earnings"}
_HIGHER_IS_USD_BEARISH = {"unemployment_rate", "unemployment_claims"}


def interpret_indicator_surprise(indicator: IndicatorName, actual: float, forecast: float) -> dict:
    """Deterministic actual-vs-forecast interpreter for the indicators
    covered in the notes -- never invents a verdict beyond what the
    documented tables say. Returns the surprise direction relative to
    forecast and the expected knock-on direction for USD, XAUUSD, and
    USD-quoted majors (EURUSD/GBPUSD move opposite USD strength).
    Equal-to-forecast is reported as inline with no directional call,
    matching the notes' own "exactly 50 = no growth, no decline" case."""
    if actual == forecast:
        surprise = "inline"
    elif indicator in _HIGHER_IS_USD_BULLISH:
        surprise = "beat" if actual > forecast else "miss"
    elif indicator in _HIGHER_IS_USD_BEARISH:
        surprise = (
            "beat" if actual < forecast else "miss"
        )  # "beat" here means better-for-USD (fewer claims/lower unemployment)
    else:
        return {
            "surprise": "unknown_indicator",
            "usd_direction": None,
            "xauusd_direction": None,
            "eur_gbp_direction": None,
            "notes": [f"'{indicator}' isn't one of the documented indicators."],
        }

    if surprise == "inline":
        return {
            "surprise": "inline",
            "usd_direction": None,
            "xauusd_direction": None,
            "eur_gbp_direction": None,
            "notes": ["Actual matched forecast -- no directional call per the documented rules."],
        }

    usd_direction = "strengthens" if surprise == "beat" else "weakens"
    xauusd_direction = "down" if surprise == "beat" else "up"
    eur_gbp_direction = "down" if surprise == "beat" else "up"

    return {
        "surprise": surprise,
        "usd_direction": usd_direction,
        "xauusd_direction": xauusd_direction,
        "eur_gbp_direction": eur_gbp_direction,
        "notes": [
            f"{indicator}: actual {actual} vs forecast {forecast} ({surprise} for USD) -> USD {usd_direction}, XAUUSD likely {xauusd_direction}, EURUSD/GBPUSD likely {eur_gbp_direction}."
        ],
    }


@dataclass
class PostNewsReentryStatus:
    phase: str  # "fake_move_window" | "confirmation_window" | "clear_for_structure_check"
    minutes_elapsed: float
    notes: list[str] = field(default_factory=list)


def post_news_reentry_status(
    event_time: datetime,
    now: datetime | None = None,
    fake_move_minutes: float = 2.0,
    confirmation_minutes: float = 5.0,
) -> PostNewsReentryStatus:
    """Implements the universal post-release waiting rule from the
    notes: don't act in the first 2 minutes (fake-move/stop-hunt
    window), treat 2-5 minutes as still needing candle-close +
    structure confirmation, and only past 5 minutes is it time to
    actually look for the real direction. This never says "safe to
    trade" outright -- even past 5 minutes it hands back to the
    structure-confirmation step (BOS/CHoCH, zone retest), same as
    should_pause_for_news() only ever pauses/doesn't-pause on imminent
    events, never confirms a trade is good on its own."""
    now = now or datetime.now(UTC)
    minutes_elapsed = (now - event_time).total_seconds() / 60

    if minutes_elapsed < 0:
        return PostNewsReentryStatus(
            phase="fake_move_window", minutes_elapsed=minutes_elapsed, notes=["Event hasn't happened yet."]
        )
    if minutes_elapsed < fake_move_minutes:
        return PostNewsReentryStatus(
            phase="fake_move_window",
            minutes_elapsed=minutes_elapsed,
            notes=[
                f"Only {minutes_elapsed:.1f} min since release -- this is the documented fake-move/stop-hunt window, do not act on it."
            ],
        )
    if minutes_elapsed < confirmation_minutes:
        return PostNewsReentryStatus(
            phase="confirmation_window",
            minutes_elapsed=minutes_elapsed,
            notes=[
                f"{minutes_elapsed:.1f} min since release -- wait for the first candle to close and for real structure confirmation before entering."
            ],
        )
    return PostNewsReentryStatus(
        phase="clear_for_structure_check",
        minutes_elapsed=minutes_elapsed,
        notes=[
            f"{minutes_elapsed:.1f} min since release -- past the fake-move window; still needs its own structure confirmation (BOS/CHoCH, zone retest) before entering, not an automatic green light."
        ],
    )
