"""Scoped-JWT database connector -- generic shared infra, not
division-specific.

Extracted from shared/systems_db_connector.py, whose get_client() had
zero Systems-specific logic in it -- minting a JWT carrying a custom
app_role claim and authenticating a Supabase REST client with it is
the exact same two-step dance regardless of which division's claim is
being minted, so it lives here once instead of being duplicated per
division (same reasoning as shared/telegram_files.py's extraction).

Each division's own table-specific helper functions (the equivalent of
systems_db_connector.py's get_circuit_breaker()/write_audit_vault())
stay in that division's own code -- only the connector mechanism moves
here, matching the project's convention that _telegram.py/
telegram_listener.py-style files carrying real division logic stay
deliberately duplicated, while logic-free plumbing doesn't.

Uses the same Supabase REST API transport as shared/db.py's
get_client() (supabase-py's create_client()), but signs a
narrowly-scoped JWT instead of using SUPABASE_SERVICE_KEY -- see
infrastructure/database/migrations/0010_systems_agent_rls_jwt.sql for
the original design rationale (Kong's two-token requirement, why RLS
policies gate on a custom app_role claim, and why this REST-based
approach was chosen over a scoped Postgres role after Supavisor
rejected that role's connections).
"""

import os
import time

import jwt
from supabase import Client, create_client

_clients: dict[str, Client] = {}
_JWT_LIFETIME_SECONDS = 10 * 365 * 24 * 60 * 60  # 10 years -- a service credential, not a user session


def _mint_scoped_jwt(app_role: str) -> str:
    secret = os.environ["SUPABASE_JWT_SECRET"]
    now = int(time.time())
    payload = {
        "role": "authenticated",
        "app_role": app_role,
        "iat": now,
        "exp": now + _JWT_LIFETIME_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def get_scoped_client(app_role: str) -> Client:
    """Two-token pattern, required by Supabase's gateway (Kong): the
    'apikey' header must be one of the project's real, known API keys
    (the public-safe anon key here) for the request to even reach
    PostgREST at all -- a custom-signed JWT there gets rejected
    outright with 'Invalid API key' before PostgREST ever evaluates
    it. The scoped JWT (carrying the given app_role claim) goes in a
    *separate* Authorization bearer, set via postgrest.auth() after
    client creation -- that's the one PostgREST actually decodes for
    RLS's auth.jwt() claims.

    Cached per app_role so repeated calls within the same process
    reuse one client -- each division's own process only ever mints
    one role in practice, but this stays correct even if that
    changes."""
    if app_role not in _clients:
        url = os.environ["SUPABASE_URL"]
        anon_key = os.environ["SUPABASE_ANON_KEY"]
        client = create_client(url, anon_key)
        client.postgrest.auth(_mint_scoped_jwt(app_role))
        _clients[app_role] = client
    return _clients[app_role]
