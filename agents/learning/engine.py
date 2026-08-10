"""Learning engine abstraction -- Learning Division.

Mohamed's explicit request (2026-08-09): keep the real, working SM-2
implementation (srs.py) as the production engine, but put a clean
interface in front of it so a different engine could be swapped in or
added later without touching content_transform.py or
telegram_listener.py -- from here on they call get_learning_engine(),
never srs.py directly.

Deliberately does NOT integrate Orbit itself -- checked live
2026-08-09: Orbit has a real REST API, but is built around Andy
Matuschak's own hosted cloud service and its own maintainer says it
"does not aspire to be a typical open-source project" -- a personal
research vehicle, not a stable product meant for third-party
self-hosted integration. This abstraction keeps that door open without
ever making Orbit, or any other engine, a hard dependency.

What's borrowed from Orbit's actual ideas, not its service:
- Contextual prompts embedded in learning material -- already real
  here: every card keeps source_type/source_reference from whatever it
  was generated from (a URL, a PDF, a video, Mohamed's own typed text).
- Active recall + spaced review -- what SM-2 already does.
- Knowledge-linked prompts -- new: learning_card_links
  (infrastructure/database/migrations/0013_learning_card_links.sql)
  lets a card reference related cards, the same bidirectional-linking
  idea Obsidian uses for notes, applied to flashcards.
"""

import os
from typing import Protocol


class LearningEngine(Protocol):
    """Structural interface every learning engine implementation must
    satisfy. Callers depend on this shape, never on a concrete
    engine's own module."""

    def add_card(
        self,
        category: str,
        front: str,
        back: str,
        source_type: str = "manual",
        source_reference: str | None = None,
    ) -> dict: ...

    def get_due_cards(self, limit: int = 20) -> list[dict]: ...

    def rate_card(self, card_id: str, rating: str) -> dict: ...

    def list_categories(self) -> list[dict]: ...

    def get_due_count(self) -> int: ...

    def link_cards(self, card_id: str, related_card_id: str) -> dict: ...

    def get_linked_cards(self, card_id: str) -> list[dict]: ...


class SM2LearningEngine:
    """The real, production engine -- a thin wrapper around srs.py's
    existing, unchanged SM-2 implementation. Every scheduling method
    here just delegates; the algorithm itself (_compute_next_state,
    etc.) is not touched or duplicated. Linking is new, owned here
    rather than in srs.py, since it's a concept the engine layer adds
    on top of SM-2, not something the algorithm itself needs to know
    about."""

    def add_card(
        self,
        category: str,
        front: str,
        back: str,
        source_type: str = "manual",
        source_reference: str | None = None,
    ) -> dict:
        from agents.learning import srs

        return srs.add_card(category, front, back, source_type=source_type, source_reference=source_reference)

    def get_due_cards(self, limit: int = 20) -> list[dict]:
        from agents.learning import srs

        return srs.get_due_cards(limit=limit)

    def rate_card(self, card_id: str, rating: str) -> dict:
        from agents.learning import srs

        return srs.rate_card(card_id, rating)

    def list_categories(self) -> list[dict]:
        from agents.learning import srs

        return srs.list_categories()

    def get_due_count(self) -> int:
        from agents.learning import srs

        return srs.get_due_count()

    def link_cards(self, card_id: str, related_card_id: str) -> dict:
        if card_id == related_card_id:
            return {"ok": False, "reason": "A card cannot be linked to itself."}

        from shared.scoped_db import get_scoped_client

        result = (
            get_scoped_client("learning_agent")
            .table("learning_card_links")
            .upsert({"card_id": card_id, "related_card_id": related_card_id}, on_conflict="card_id,related_card_id")
            .execute()
        )
        return {"ok": True, "link": result.data[0] if result.data else None}

    def get_linked_cards(self, card_id: str) -> list[dict]:
        """Bidirectional -- a link created in either direction shows up
        from either card's perspective, matching how Obsidian's
        backlinks work."""
        from shared.scoped_db import get_scoped_client

        client = get_scoped_client("learning_agent")
        forward = client.table("learning_card_links").select("related_card_id").eq("card_id", card_id).execute()
        backward = client.table("learning_card_links").select("card_id").eq("related_card_id", card_id).execute()

        linked_ids = {row["related_card_id"] for row in forward.data} | {row["card_id"] for row in backward.data}
        if not linked_ids:
            return []

        cards = client.table("learning_cards").select("*").in_("id", list(linked_ids)).execute()
        return cards.data


_ENGINES: dict[str, type] = {"sm2": SM2LearningEngine}


def get_learning_engine() -> LearningEngine:
    """LEARNING_ENGINE env var picks the engine, defaults to "sm2" --
    the real, production one. Nothing else is implemented today; this
    is the one place a future engine would be registered, without any
    caller ever needing to change."""
    engine_name = os.environ.get("LEARNING_ENGINE", "sm2").lower()
    engine_cls = _ENGINES.get(engine_name, SM2LearningEngine)
    return engine_cls()
