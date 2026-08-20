from unittest.mock import patch

from agents.rii import watchtower as wt

WATCHTOWER = {
    "id": "wt-1",
    "topic": "AI Empire University curriculum trends",
    "seen_urls": ["https://old.example/1"],
}


def test_check_one_watchtower_logs_on_search_failure():
    with (
        patch("agents.rii.research.web_search", return_value={"ok": False, "reason": "Tavily unavailable"}),
        patch("agents.rii._memory_helpers.safe_add_experience") as mock_log,
    ):
        result = wt.check_one_watchtower(WATCHTOWER)

    assert result == {"ok": False, "reason": "Tavily unavailable"}
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["outcome"] == "search_failed"
    assert mock_log.call_args.kwargs["context"] == WATCHTOWER["topic"]


def test_check_one_watchtower_logs_ok_and_updates_seen_urls_on_success():
    fake_results = {
        "ok": True,
        "results": [
            {"url": "https://old.example/1", "title": "old"},
            {"url": "https://new.example/2", "title": "new"},
        ],
    }
    mock_table = patch("shared.scoped_db.get_scoped_client")
    with (
        patch("agents.rii.research.web_search", return_value=fake_results),
        patch("agents.rii._memory_helpers.safe_add_experience") as mock_log,
        mock_table as mock_get_client,
    ):
        result = wt.check_one_watchtower(WATCHTOWER)

    assert result["ok"] is True
    assert result["new_results"] == [{"url": "https://new.example/2", "title": "new"}]
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["outcome"] == "ok"
    assert mock_log.call_args.kwargs["metadata"]["new_results_count"] == 1
    mock_get_client.assert_called_once_with("rii_agent")


def test_check_all_watchtowers_logs_a_crash_instead_of_swallowing_it_silently():
    with (
        patch.object(wt, "list_watchtowers", return_value=[WATCHTOWER]),
        patch.object(wt, "check_one_watchtower", side_effect=RuntimeError("db exploded")),
        patch("agents.rii._memory_helpers.safe_add_experience") as mock_log,
        patch("agents.rii._telegram.send_telegram") as mock_telegram,
    ):
        result = wt.check_all_watchtowers()

    assert result == {"checked": 0, "alerts_sent": 0}
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["outcome"] == "crashed"
    assert mock_log.call_args.kwargs["context"] == WATCHTOWER["topic"]
    assert "db exploded" in mock_log.call_args.kwargs["metadata"]["reason"]
    mock_telegram.assert_not_called()


def test_check_all_watchtowers_sends_alert_only_when_there_are_new_results():
    with (
        patch.object(wt, "list_watchtowers", return_value=[WATCHTOWER]),
        patch.object(
            wt,
            "check_one_watchtower",
            return_value={"ok": True, "new_results": [{"title": "New Thing", "url": "https://new.example"}]},
        ),
        patch("agents.rii._telegram.send_telegram") as mock_telegram,
    ):
        result = wt.check_all_watchtowers()

    assert result == {"checked": 1, "alerts_sent": 1}
    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert WATCHTOWER["topic"] in sent_message
    assert "New Thing" in sent_message


def test_check_all_watchtowers_skips_alert_when_nothing_new():
    with (
        patch.object(wt, "list_watchtowers", return_value=[WATCHTOWER]),
        patch.object(wt, "check_one_watchtower", return_value={"ok": True, "new_results": []}),
        patch("agents.rii._telegram.send_telegram") as mock_telegram,
    ):
        result = wt.check_all_watchtowers()

    assert result == {"checked": 1, "alerts_sent": 0}
    mock_telegram.assert_not_called()
