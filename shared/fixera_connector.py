"""Scoped, read-only connector to Fixera's production database.

Connects as the ai_empire_reader Postgres role, which has SELECT-only
access to exactly 5 narrow views (ai_empire_bookings_summary,
ai_empire_payments_summary, ai_empire_disputes_summary,
ai_empire_reviews_summary, ai_empire_workers_summary) -- see
infrastructure/fixera_connector_reference.sql for the view definitions
and what's deliberately excluded (PII, OTPs, national IDs, free-text
statements, etc.) and CONTEXT.md's "Fixera Relationship" section for
why this exists as a separate connection rather than sharing Fixera's
own Supabase credentials.
"""

import os
import time
from typing import Any, Optional

import psycopg2
import psycopg2.extras

_conn = None

# Fixera's Supabase pooler (Supavisor) appears to run multiple backend
# nodes behind one hostname that don't all have a newly-created role's
# credentials cached at the same time -- observed directly: identical
# connection attempts intermittently succeed and fail with "password
# authentication failed" against the exact same, verified-correct
# credentials. A short retry ride out is a legitimate fix for that, not
# a workaround for a real credential problem.
_CONNECT_RETRIES = 4
_CONNECT_RETRY_DELAY_SECONDS = 2


def _connect_with_retry():
    last_error = None
    for attempt in range(_CONNECT_RETRIES):
        try:
            return psycopg2.connect(
                host=os.environ["FIXERA_DB_HOST"],
                port=os.environ["FIXERA_DB_PORT"],
                dbname=os.environ["FIXERA_DB_NAME"],
                user=os.environ["FIXERA_DB_USER"],
                password=os.environ["FIXERA_DB_PASSWORD"],
                sslmode="require",
                connect_timeout=15,
            )
        except psycopg2.OperationalError as e:
            last_error = e
            if attempt < _CONNECT_RETRIES - 1:
                time.sleep(_CONNECT_RETRY_DELAY_SECONDS)
    raise last_error


def _get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = _connect_with_retry()
    return _conn


_ALLOWED_VIEWS = {
    "bookings": "ai_empire_bookings_summary",
    "payments": "ai_empire_payments_summary",
    "disputes": "ai_empire_disputes_summary",
    "reviews": "ai_empire_reviews_summary",
    "workers": "ai_empire_workers_summary",
}


def fetch_all(resource: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
    """resource is one of the keys in _ALLOWED_VIEWS ('bookings',
    'payments', 'disputes', 'reviews', 'workers') -- deliberately not a
    raw SQL passthrough, so callers can't accidentally query outside the
    5 sanctioned views."""
    if resource not in _ALLOWED_VIEWS:
        raise ValueError(f"Unknown Fixera resource '{resource}'. Allowed: {sorted(_ALLOWED_VIEWS)}")

    view = _ALLOWED_VIEWS[resource]
    query = f"SELECT * FROM {view}"
    if limit is not None:
        query += f" LIMIT {int(limit)}"

    conn = _get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]
