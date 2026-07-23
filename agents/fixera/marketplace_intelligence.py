"""Marketplace Intelligence Agent v0.1 — Fixera Division.

Strategic improvement: demand patterns, partner utilization, pricing
signals, bottleneck detection. Built against mock data matching
ai_empire_bookings_summary / ai_empire_workers_summary (connector
still unresolved -- see CONTEXT.md).

Operates in Research Mode by default per its own Boundaries: read-only
analysis, output is recommendations only, never autonomous pricing or
policy changes.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class DemandSignal:
    service: str
    booking_count: int
    completed_count: int
    cancelled_count: int
    completion_rate: float


def demand_by_service(bookings: list[dict[str, Any]]) -> list[DemandSignal]:
    """Booking volume and completion/cancellation rates per service --
    surfaces which services are in demand and which are struggling."""
    by_service: dict[str, Counter] = defaultdict(Counter)
    for booking in bookings:
        service = booking.get("service") or "unknown"
        by_service[service]["total"] += 1
        status = booking.get("status")
        if status == "completed":
            by_service[service]["completed"] += 1
        elif status == "cancelled":
            by_service[service]["cancelled"] += 1

    signals = []
    for service, counts in by_service.items():
        total = counts["total"]
        completed = counts["completed"]
        rate = completed / total if total else 0.0
        signals.append(DemandSignal(service, total, completed, counts["cancelled"], round(rate, 3)))
    return sorted(signals, key=lambda s: -s.booking_count)


@dataclass
class UtilizationSignal:
    service: str
    eligible_worker_count: int
    open_booking_count: int
    ratio: float  # bookings per eligible worker -- high = bottleneck risk


def partner_utilization(bookings: list[dict[str, Any]], workers: list[dict[str, Any]]) -> list[UtilizationSignal]:
    """Flags services where demand (open bookings) is outpacing available
    supply (eligible workers) -- a capacity bottleneck signal."""
    open_statuses = {"pending", "upcoming", "confirmed", "arrived", "in_progress"}
    open_by_service: Counter = Counter()
    for booking in bookings:
        if booking.get("status") in open_statuses:
            open_by_service[booking.get("service") or "unknown"] += 1

    available_by_service: Counter = Counter()
    for worker in workers:
        if worker.get("status") == "online" or worker.get("is_available"):
            available_by_service[worker.get("service") or "unknown"] += 1

    services = set(open_by_service) | set(available_by_service)
    signals = []
    for service in services:
        open_count = open_by_service.get(service, 0)
        worker_count = available_by_service.get(service, 0)
        ratio = (open_count / worker_count) if worker_count else float("inf") if open_count else 0.0
        signals.append(UtilizationSignal(service, worker_count, open_count, ratio if ratio != float("inf") else 999.0))
    return sorted(signals, key=lambda s: -s.ratio)


def bottleneck_services(signals: list[UtilizationSignal], ratio_threshold: float = 3.0) -> list[UtilizationSignal]:
    """Filters utilization signals down to services where demand
    meaningfully outstrips supply -- a recommendation to review pricing
    or recruit more partners, never an automatic action."""
    return [s for s in signals if s.ratio >= ratio_threshold]
