"""Research Agent v0.1 -- Forex Division.

Per the actual design (AI_EMPIRE_Master_Governance_v2.docx §3.1,
Implementation_Roadmap_v1.docx §5.4): Research is the first of three
gated stages (Research 40% / Technical Analysis 30% / Trading
Psychology 30%) that must all pass before a trade proceeds through the
Execution Gate. This agent's job is market reports, trade ideas, and
risk alerts -- Source Reliability and Behavioral Confidence required,
per the governance doc's Research Mode requirements.

Data sources (all free, no API key required):
  - ForexFactory's calendar feed (widely used, unofficial JSON) for
    scheduled economic events with impact ratings.
  - Fed / ECB / BOE / BOJ / SNB press-release RSS feeds for official
    statements the moment they're published. BOJ and SNB added
    2026-07-26 alongside the pair-list expansion (USDJPY, USDCHF) --
    each individually verified as a real, working feed before adding
    (never guessed). RBA (for AUDUSD) was researched too but its
    feed actively returns 403 Forbidden even from a plain requests.get
    with a browser user-agent -- not addable right now, a real gap,
    not silently worked around. AUD news still reaches the pipeline via
    the ForexFactory calendar below, just without a dedicated RBA
    statement feed.

Scoped to the pairs the user actually trades (expanded 2026-07-26:
EURUSD, GBPUSD, USDCAD, USDJPY, USDCHF, AUDUSD, XAUUSD, NAS100), which
map to USD, EUR, GBP, CAD, JPY, CHF, AUD as the currencies worth
tracking -- everything else is noise for this account.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import requests

FOREXFACTORY_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

CENTRAL_BANK_FEEDS = {
    "Fed": "https://www.federalreserve.gov/feeds/press_all.xml",
    "ECB": "https://www.ecb.europa.eu/rss/press.html",
    "BOE": "https://www.bankofengland.co.uk/rss/news",
    "BOJ": "https://www.boj.or.jp/en/rss/whatsnew.xml",
    "SNB": "https://www.snb.ch/public/en/rss/news",
}

RELEVANT_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "JPY", "CHF", "AUD"}
ALERT_IMPACT_LEVELS = {"Medium", "High"}


@dataclass
class CalendarEvent:
    title: str
    country: str
    date: Optional[datetime]
    impact: str
    forecast: str
    previous: str


@dataclass
class CentralBankItem:
    bank: str
    title: str
    link: Optional[str]


@dataclass
class MarketReport:
    generated_at: datetime
    relevant_events: list[CalendarEvent] = field(default_factory=list)
    central_bank_items: list[CentralBankItem] = field(default_factory=list)

    def summary_text(self) -> str:
        lines = [f"Forex market report -- {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"]
        if self.relevant_events:
            lines.append("\nUpcoming/recent high-relevance calendar events:")
            for e in self.relevant_events:
                when = e.date.strftime("%a %H:%M") if e.date else "time unknown"
                lines.append(f"  - [{e.impact}] {e.country} {e.title} ({when}) forecast={e.forecast or 'n/a'} previous={e.previous or 'n/a'}")
        if self.central_bank_items:
            lines.append("\nRecent central bank statements:")
            for item in self.central_bank_items:
                lines.append(f"  - [{item.bank}] {item.title}")
        if not self.relevant_events and not self.central_bank_items:
            lines.append("\nNothing high-relevance found this pull.")
        return "\n".join(lines)


def fetch_forexfactory_calendar(timeout: int = 15) -> list[CalendarEvent]:
    resp = requests.get(FOREXFACTORY_CALENDAR_URL, timeout=timeout)
    resp.raise_for_status()
    events = []
    for row in resp.json():
        date_str = row.get("date")
        parsed_date = None
        if date_str:
            try:
                parsed_date = datetime.fromisoformat(date_str)
            except ValueError:
                parsed_date = None
        events.append(CalendarEvent(
            title=row.get("title", ""), country=row.get("country", ""),
            date=parsed_date, impact=row.get("impact", ""),
            forecast=row.get("forecast", ""), previous=row.get("previous", ""),
        ))
    return events


def fetch_central_bank_items(bank: str, timeout: int = 15, limit: int = 5) -> list[CentralBankItem]:
    url = CENTRAL_BANK_FEEDS[bank]
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for item_el in root.findall(".//item")[:limit]:
        title_el = item_el.find("title")
        link_el = item_el.find("link")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else None
        if title:
            items.append(CentralBankItem(bank=bank, title=title, link=link))
    return items


def filter_relevant_events(
    events: list[CalendarEvent],
    currencies: set[str] = RELEVANT_CURRENCIES,
    impact_levels: set[str] = ALERT_IMPACT_LEVELS,
) -> list[CalendarEvent]:
    return [e for e in events if e.country in currencies and e.impact in impact_levels]


def build_market_report() -> MarketReport:
    """Live entry point: pulls all free data sources, filters for
    relevance, returns a structured report. Never raises on a single
    source failing -- a down feed shouldn't block the whole report."""
    report = MarketReport(generated_at=datetime.now(timezone.utc))

    try:
        all_events = fetch_forexfactory_calendar()
        report.relevant_events = filter_relevant_events(all_events)
    except requests.RequestException:
        pass

    for bank in CENTRAL_BANK_FEEDS:
        try:
            report.central_bank_items.extend(fetch_central_bank_items(bank))
        except (requests.RequestException, ET.ParseError):
            continue

    return report


def run_research_sweep() -> MarketReport:
    """Builds a fresh market report and logs it to memory_knowledge
    (division="forex") so other Forex agents -- and the CEO/Lead agent
    once it exists -- can query it. Returns the report either way."""
    from agents.forex._memory_helpers import safe_add_knowledge

    report = build_market_report()
    safe_add_knowledge(
        division="forex",
        agent_id="forex-research-v0.1",
        content=report.summary_text(),
        source="forexfactory+central_bank_rss",
        metadata={
            "generated_at": report.generated_at.isoformat(),
            "event_count": len(report.relevant_events),
            "central_bank_item_count": len(report.central_bank_items),
        },
    )
    return report
