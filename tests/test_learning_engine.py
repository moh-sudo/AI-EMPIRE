"""Real tests for the Learning Division engine abstraction
(agents/learning/engine.py) -- added 2026-08-09 so the production SM-2
implementation (srs.py) could be swapped or extended later without
touching content_transform.py or telegram_listener.py. Delegation to
srs.py and the DB are mocked out -- no real Supabase, no real network
calls, safe to run anywhere including CI.
"""

import os
from unittest.mock import MagicMock, patch

from agents.learning import engine as engine_module
from agents.learning.engine import SM2LearningEngine, get_learning_engine


def test_default_engine_is_sm2():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("LEARNING_ENGINE", None)
        assert isinstance(get_learning_engine(), SM2LearningEngine)


def test_unknown_engine_name_falls_back_to_sm2():
    with patch.dict(os.environ, {"LEARNING_ENGINE": "orbit"}):
        assert isinstance(get_learning_engine(), SM2LearningEngine)


def test_engine_registry_is_explicit():
    """A future engine (Orbit or otherwise) gets added here -- guards
    against someone assuming registration happens some other way."""
    assert set(engine_module._ENGINES) == {"sm2"}


def test_sm2_add_card_delegates_to_srs():
    eng = SM2LearningEngine()
    with patch("agents.learning.srs.add_card", return_value={"id": "abc"}) as mock_add:
        result = eng.add_card(
            "linux",
            "what is a pipe?",
            "connects stdout to stdin",
            source_type="url",
            source_reference="http://example.com",
        )
    mock_add.assert_called_once_with(
        "linux", "what is a pipe?", "connects stdout to stdin", source_type="url", source_reference="http://example.com"
    )
    assert result == {"id": "abc"}


def test_sm2_rate_card_delegates_to_srs():
    eng = SM2LearningEngine()
    with patch("agents.learning.srs.rate_card", return_value={"ok": True}) as mock_rate:
        eng.rate_card("card-1", "GOOD")
    mock_rate.assert_called_once_with("card-1", "GOOD")


def test_link_cards_rejects_self_link():
    eng = SM2LearningEngine()
    result = eng.link_cards("card-1", "card-1")
    assert result["ok"] is False
    assert "itself" in result["reason"]


def test_link_cards_writes_via_upsert():
    eng = SM2LearningEngine()
    fake_client = MagicMock()
    fake_client.table.return_value.upsert.return_value.execute.return_value.data = [
        {"card_id": "a", "related_card_id": "b"}
    ]
    with patch("shared.scoped_db.get_scoped_client", return_value=fake_client):
        result = eng.link_cards("a", "b")

    assert result["ok"] is True
    fake_client.table.assert_called_with("learning_card_links")
    fake_client.table.return_value.upsert.assert_called_once_with(
        {"card_id": "a", "related_card_id": "b"}, on_conflict="card_id,related_card_id"
    )


def test_get_linked_cards_is_bidirectional():
    """A link stored as (a -> b) must show up when querying from b's
    side too -- matches how Obsidian backlinks work, the concept this
    was explicitly built to borrow."""
    eng = SM2LearningEngine()
    fake_client = MagicMock()

    def table_side_effect(name):
        m = MagicMock()
        if name == "learning_card_links":
            # forward query (card_id == 'b') returns nothing; backward
            # query (related_card_id == 'b') finds the a->b link.
            def select_side_effect(*_args, **_kwargs):
                sel = MagicMock()

                def eq_side_effect(col, val):
                    e = MagicMock()
                    if col == "card_id":
                        e.execute.return_value.data = []
                    elif col == "related_card_id":
                        e.execute.return_value.data = [{"card_id": "a"}]
                    return e

                sel.eq.side_effect = eq_side_effect
                return sel

            m.select.side_effect = select_side_effect
        elif name == "learning_cards":
            m.select.return_value.in_.return_value.execute.return_value.data = [{"id": "a", "front": "Q"}]
        return m

    fake_client.table.side_effect = table_side_effect

    with patch("shared.scoped_db.get_scoped_client", return_value=fake_client):
        linked = eng.get_linked_cards("b")

    assert len(linked) == 1
    assert linked[0]["id"] == "a"


def test_get_linked_cards_returns_empty_without_a_query_when_no_links():
    eng = SM2LearningEngine()
    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("shared.scoped_db.get_scoped_client", return_value=fake_client):
        linked = eng.get_linked_cards("lonely-card")

    assert linked == []
