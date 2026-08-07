"""Performance Monitoring -- Audit & Verification Division.

Real timing of each division's key report-generation operations --
found the Personal Division's Morning Brief was slow (94s) exactly
this way earlier the same day, informally; this makes that kind of
check permanent and automatic instead of one-off. Fully deterministic
(timing + comparison against real historical data), no LLM needed.
"""

from collections.abc import Callable

# (division, operation, callable) -- each callable is a real live
# entry point already built and used elsewhere; this doesn't duplicate
# their logic, just times them.
_MONITORED_OPERATIONS: list[tuple[str, str, Callable]] = []


def _load_operations() -> list[tuple[str, str, Callable]]:
    """Lazy import -- avoids circular imports and avoids failing this
    whole module if one division's code has a problem."""
    ops = []
    try:
        from agents.fixera.ceo_lead import run_daily_briefing as fixera_brief

        ops.append(("fixera", "daily_briefing", fixera_brief))
    except Exception:
        pass
    try:
        from agents.forex.ceo_lead import run_daily_briefing as forex_brief

        ops.append(("forex", "daily_briefing", forex_brief))
    except Exception:
        pass
    try:
        from agents.personal.morning_brief import build_morning_brief

        ops.append(("personal", "morning_brief", build_morning_brief))
    except Exception:
        pass
    return ops


DEGRADATION_THRESHOLD_MULTIPLIER = 2.0  # flag if >2x the historical average


def _record_timing(division: str, operation: str, duration_seconds: float, ok: bool) -> None:
    from shared.db import get_client

    get_client().table("audit_performance_log").insert(
        {
            "division": division,
            "operation": operation,
            "duration_seconds": round(duration_seconds, 3),
            "ok": ok,
        }
    ).execute()


def _get_historical_average(
    division: str, operation: str, exclude_latest: bool = True, limit: int = 10
) -> float | None:
    from shared.db import get_client

    query = (
        get_client()
        .table("audit_performance_log")
        .select("duration_seconds")
        .eq("division", division)
        .eq("operation", operation)
        .eq("ok", True)
        .order("created_at", desc=True)
        .limit(limit + (1 if exclude_latest else 0))
        .execute()
    )
    rows = query.data
    if exclude_latest and rows:
        rows = rows[1:]  # drop the just-recorded run
    if not rows:
        return None
    return sum(r["duration_seconds"] for r in rows) / len(rows)


def run_performance_check() -> dict:
    """Live entry point -- times every monitored operation for real,
    records it, and flags anything running significantly slower than
    its own historical average. Each operation isolated in its own
    try/except."""
    import time

    findings = []
    checked = []

    for division, operation, fn in _load_operations():
        start = time.time()
        ok = True
        try:
            fn()
        except Exception:
            ok = False
        duration = time.time() - start

        try:
            _record_timing(division, operation, duration, ok)
        except Exception:
            pass  # logging failure shouldn't block the check itself

        checked.append({"division": division, "operation": operation, "duration_seconds": round(duration, 2), "ok": ok})

        if not ok:
            findings.append({"division": division, "operation": operation, "issue": "operation failed"})
            continue

        avg = _get_historical_average(division, operation)
        if avg is not None and duration > avg * DEGRADATION_THRESHOLD_MULTIPLIER:
            findings.append(
                {
                    "division": division,
                    "operation": operation,
                    "issue": f"took {duration:.1f}s, more than {DEGRADATION_THRESHOLD_MULTIPLIER}x its historical average ({avg:.1f}s)",
                }
            )

    return {"checked": checked, "findings": findings}
