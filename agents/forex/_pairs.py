"""Shared traded-pairs list, trading-day schedule, and priority tier --
Forex Division. Single source of truth: TRADED_PAIRS/similar constants
used to be independently duplicated in strategy.py and
market_analytics.py -- consolidated here (2026-07-26) once Mohamed
expanded the pair list, so adding/removing a pair is a one-line change
here instead of a hunt across files that could silently drift apart.

Per Mohamed's own explicit correction (2026-07-26): this is a WATCHLIST,
not a mandate. Being in TRADED_PAIRS/PAIR_TRADING_DAYS means a pair is
ELIGIBLE to trade on a given day if a real setup appears -- it does not
mean that pair must be traded every eligible day. The actual daily cap
(2 trades/day, regardless of how many pairs show an opportunity) lives
in agents/forex/risk_management.py (MAX_TRADES_PER_DAY /
check_trade_count_status), since that's a risk/discipline concern, not
a pairs concern.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

ALL_WEEKDAYS = {"Mon", "Tue", "Wed", "Thu", "Fri"}

# XAUUSD trades only 3 days/week (Mohamed's own explicit schedule,
# 2026-07-26); every other pair trades all 5 weekdays.
PAIR_TRADING_DAYS: dict[str, set[str]] = {
    "EURUSD": ALL_WEEKDAYS,
    "GBPUSD": ALL_WEEKDAYS,
    "USDCAD": ALL_WEEKDAYS,
    "USDJPY": ALL_WEEKDAYS,
    "USDCHF": ALL_WEEKDAYS,
    "AUDUSD": ALL_WEEKDAYS,
    "NAS100": ALL_WEEKDAYS,
    "XAUUSD": {"Tue", "Wed", "Thu"},
}

TRADED_PAIRS = set(PAIR_TRADING_DAYS.keys())

# "More eyes" tier -- Mohamed's own explicit emphasis (2026-07-26).
# GBPUSD and AUDUSD are tradeable but NOT in this priority tier.
PRIORITY_PAIRS = {"EURUSD", "USDJPY", "XAUUSD", "USDCAD", "USDCHF", "NAS100"}

NY_TZ = ZoneInfo("America/New_York")
_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def current_ny_weekday() -> str:
    """Uses zoneinfo (needs the tzdata package on Windows, installed
    2026-07-26 -- Windows doesn't ship the IANA tz database by default)
    so DST transitions are handled correctly automatically, rather than
    a fixed UTC-offset approximation that would silently drift wrong
    twice a year."""
    return _WEEKDAY_NAMES[datetime.now(NY_TZ).weekday()]


def is_pair_tradeable_today(pair: str, weekday: Optional[str] = None) -> bool:
    """weekday defaults to today's actual NY weekday if not given.
    Returns False for any pair not in PAIR_TRADING_DAYS at all, same
    fail-closed spirit as the rest of this division -- an unrecognized
    pair is never silently assumed tradeable."""
    pair_upper = pair.upper()
    if pair_upper not in PAIR_TRADING_DAYS:
        return False
    if weekday is None:
        weekday = current_ny_weekday()
    return weekday in PAIR_TRADING_DAYS[pair_upper]
