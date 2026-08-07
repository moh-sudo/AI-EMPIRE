"""Marketplace Price Regulation -- Fixera Division.

Fixera's own app (worker/src/services/supplierProductService.js,
migrations/add_product_approval.sql) already gates every new product
and every price change behind Mohamed's admin-dashboard approval --
new rows default to status='pending', price changes go into
pending_price, and the live price stays untouched until he approves.
What was actually missing was a notification: nothing pinged Mohamed
when something was waiting, so he'd only find out by checking the
dashboard himself. That's the entire job of this agent -- alert on
Telegram, never approve/reject/change anything. Deliberately no LLM
call: every check below is deterministic (a price percentage
comparison), so per Mohamed's 2026-07-31 instruction to build
architecture first and connect a real LLM only once he has bigger
hardware, this agent needed no stub at all -- it's fully real today.

Comparison basis: other Fixera vendors/suppliers' already-APPROVED
prices in the same category (Mohamed's explicit choice -- internal
comparison, not an external market-data source). With Fixera's
marketplace still young, most categories will have too few comparison
points to say anything meaningful yet -- that's reported honestly as
"not enough data", never a fabricated verdict from 1-2 data points.
"""

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STATE_FILE = Path(__file__).resolve().parent / ".marketplace_price_regulation_seen.json"

MIN_COMPARISON_POINTS = 3  # below this, comparison is unreliable -- say so, don't guess

# Thresholds against the category's average approved price.
GOUGING_RATIO = 1.5  # > 50% above average
UNDERCUTTING_RATIO = 0.5  # < 50% below average
LISTING_ERROR_HIGH_RATIO = 5.0  # > 5x average -- almost certainly a typo, not a real price
LISTING_ERROR_LOW_RATIO = 0.2  # < 1/5 of average -- same, other direction


@dataclass
class PriceFlag:
    product_id: str
    supplier_name: str | None
    business_name: str | None
    product_name: str
    category: str | None
    price: float
    is_price_change: bool
    flag_type: str | None = None  # 'gouging' | 'undercutting' | 'possible_listing_error' | None
    comparison_note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _read_seen() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        return set(json.loads(STATE_FILE.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_seen(seen: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(seen)))


def _seen_key(product: dict[str, Any]) -> str:
    """A product is re-notified if its pending_price changes (a fresh
    proposal), not just because it's still sitting pending -- keyed on
    id + whatever value is actually awaiting approval."""
    pending_marker = product.get("pending_price")
    return f"{product['id']}::{pending_marker}"


def _effective_price(product: dict[str, Any]) -> float:
    """The price actually awaiting approval: pending_price if one is
    proposed, otherwise the (also-pending) initial price for a brand
    new product."""
    if product.get("pending_price") is not None:
        return float(product["pending_price"])
    return float(product.get("price") or 0)


def _category_average(category: str | None, approved_products: list[dict[str, Any]]) -> tuple[float | None, int]:
    prices = [
        float(p["price"]) for p in approved_products if p.get("category") == category and p.get("price") is not None
    ]
    if not prices:
        return None, 0
    return statistics.mean(prices), len(prices)


def _classify(price: float, average: float | None, n: int) -> tuple[str | None, str]:
    if average is None or n < MIN_COMPARISON_POINTS:
        return None, f"not enough data to compare ({n} other approved listing(s) in this category)"

    ratio = price / average if average else 0
    note = f"{price:,.0f} vs category average {average:,.0f} ({n} listings) -- {ratio:.1f}x"

    if ratio >= LISTING_ERROR_HIGH_RATIO or ratio <= LISTING_ERROR_LOW_RATIO:
        return "possible_listing_error", note
    if ratio >= GOUGING_RATIO:
        return "gouging", note
    if ratio <= UNDERCUTTING_RATIO:
        return "undercutting", note
    return None, note


def _build_message(flag: PriceFlag) -> str:
    kind = "NEW PRODUCT" if not flag.is_price_change else "PRICE CHANGE"
    supplier = flag.business_name or flag.supplier_name or "(unknown supplier)"
    lines = [
        f"[Marketplace] {kind} awaiting your approval",
        f"Supplier: {supplier}",
        f"Item: {flag.product_name} ({flag.category or 'uncategorized'})",
        f"Price: KSh {flag.price:,.0f}",
    ]
    if flag.flag_type == "possible_listing_error":
        lines.append(f"WARNING: looks like a possible listing error -- {flag.comparison_note}")
    elif flag.flag_type == "gouging":
        lines.append(f"WARNING: priced well above similar listings -- {flag.comparison_note}")
    elif flag.flag_type == "undercutting":
        lines.append(f"NOTE: priced well below similar listings -- {flag.comparison_note}")
    else:
        lines.append(flag.comparison_note)
    lines.append("Review and approve/reject in the Fixera admin dashboard.")
    return "\n".join(lines)


def run_new_listings_sweep(notify: bool = True) -> dict:
    """Live entry point: finds every pending new product and every
    pending price change not already notified, classifies each against
    its category's approved-price average, and (if notify=True) sends
    one Telegram message per item via Fixera's dedicated bot. Never
    raises -- same fail-safe pattern as every other agent in this
    division."""
    from shared.fixera_connector import fetch_all

    try:
        products = fetch_all("products")
    except Exception as e:
        return {"checked": False, "reason": str(e)}

    approved = [p for p in products if p.get("status") == "approved"]
    pending_or_changed = [p for p in products if p.get("status") == "pending" or p.get("pending_price") is not None]

    seen = _read_seen()
    new_flags: list[PriceFlag] = []

    for p in pending_or_changed:
        key = _seen_key(p)
        if key in seen:
            continue
        price = _effective_price(p)
        average, n = _category_average(p.get("category"), approved)
        flag_type, note = _classify(price, average, n)
        new_flags.append(
            PriceFlag(
                product_id=p["id"],
                supplier_name=p.get("supplier_name"),
                business_name=p.get("business_name"),
                product_name=p.get("product_name") or "(unnamed product)",
                category=p.get("category"),
                price=price,
                is_price_change=p.get("pending_price") is not None and p.get("status") == "approved",
                flag_type=flag_type,
                comparison_note=note,
            )
        )
        seen.add(key)

    sent = 0
    if notify and new_flags:
        from agents.fixera._telegram import send_telegram

        for flag in new_flags:
            result = send_telegram(_build_message(flag), token_env="TELEGRAM_FIXERA_BOT_TOKEN")
            if result.get("sent"):
                sent += 1

    _save_seen(seen)

    return {
        "checked": True,
        "new_items": len(new_flags),
        "telegram_sent": sent,
        "flags": [f.__dict__ for f in new_flags],
    }
