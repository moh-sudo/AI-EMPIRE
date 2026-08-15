from unittest.mock import MagicMock, patch

from agents.systems import ci_health_monitor as chm


def _mock_response(json_data, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_data
    if not status_ok:
        resp.raise_for_status.side_effect = chm.requests.RequestException("boom")
    return resp


def test_fetch_latest_master_run_fails_closed_when_token_missing():
    with patch.dict("os.environ", {}, clear=True):
        result = chm.fetch_latest_master_run()
    assert result["ok"] is False
    assert "GITHUB_TOKEN not configured" in result["reason"]


def test_fetch_latest_master_run_reports_no_runs_found():
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "fake"}),
        patch.object(chm.requests, "get", return_value=_mock_response({"workflow_runs": []})),
    ):
        result = chm.fetch_latest_master_run()
    assert result == {"ok": False, "reason": "No CI runs found on master."}


def test_fetch_latest_master_run_reports_in_progress_run_honestly():
    run = {"id": 42, "status": "in_progress", "conclusion": None}
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "fake"}),
        patch.object(chm.requests, "get", return_value=_mock_response({"workflow_runs": [run]})),
    ):
        result = chm.fetch_latest_master_run()
    assert result["ok"] is False
    assert "still in_progress" in result["reason"]


def test_fetch_latest_master_run_parses_a_completed_run():
    run = {
        "id": 42,
        "status": "completed",
        "conclusion": "success",
        "head_sha": "abc1234567",
        "head_commit": {"message": "Fix the thing\n\nlonger body"},
        "html_url": "https://github.com/moh-sudo/AI-EMPIRE/actions/runs/42",
    }
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "fake"}),
        patch.object(chm.requests, "get", return_value=_mock_response({"workflow_runs": [run]})),
    ):
        result = chm.fetch_latest_master_run()
    assert result == {
        "ok": True,
        "run_id": 42,
        "conclusion": "success",
        "head_sha": "abc1234567",
        "commit_message": "Fix the thing\n\nlonger body",
        "html_url": "https://github.com/moh-sudo/AI-EMPIRE/actions/runs/42",
    }


def test_fetch_latest_master_run_handles_missing_head_commit():
    run = {
        "id": 42,
        "status": "completed",
        "conclusion": "failure",
        "head_sha": "abc1234567",
        "head_commit": None,
        "html_url": "https://x",
    }
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "fake"}),
        patch.object(chm.requests, "get", return_value=_mock_response({"workflow_runs": [run]})),
    ):
        result = chm.fetch_latest_master_run()
    assert result["commit_message"] == ""


def test_fetch_failed_steps_returns_empty_without_token():
    with patch.dict("os.environ", {}, clear=True):
        assert chm.fetch_failed_steps(42) == []


def test_fetch_failed_steps_names_the_broken_step():
    jobs_response = {
        "jobs": [
            {
                "name": "lint-and-test",
                "steps": [
                    {"name": "ruff check", "conclusion": "success"},
                    {"name": "pytest", "conclusion": "failure"},
                ],
            }
        ]
    }
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "fake"}),
        patch.object(chm.requests, "get", return_value=_mock_response(jobs_response)),
    ):
        result = chm.fetch_failed_steps(42)
    assert result == ["lint-and-test / pytest"]


def test_fetch_failed_steps_fails_soft_on_api_error():
    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "fake"}),
        patch.object(chm.requests, "get", side_effect=chm.requests.RequestException("boom")),
    ):
        result = chm.fetch_failed_steps(42)
    assert result == []


def test_run_ci_health_sweep_fails_closed_on_fetch_failure():
    with patch.object(chm, "fetch_latest_master_run", return_value={"ok": False, "reason": "no token"}):
        result = chm.run_ci_health_sweep()
    assert result == {"ok": False, "stage": "fetch", "reason": "no token"}


def test_run_ci_health_sweep_establishes_baseline_silently_on_first_check():
    run = {
        "ok": True,
        "run_id": 1,
        "conclusion": "success",
        "head_sha": "abc",
        "commit_message": "init",
        "html_url": "https://x",
    }
    with (
        patch.object(chm, "fetch_latest_master_run", return_value=run),
        patch.object(chm, "_get_last_known_conclusion", return_value=None),
        patch("agents.systems._telegram.send_telegram") as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = chm.run_ci_health_sweep()

    mock_telegram.assert_not_called()
    mock_vault.assert_called_once()
    assert result == {"ok": True, "state_changed": False, "conclusion": "success", "failed_steps": []}


def test_run_ci_health_sweep_does_nothing_when_state_unchanged():
    run = {
        "ok": True,
        "run_id": 2,
        "conclusion": "success",
        "head_sha": "abc",
        "commit_message": "x",
        "html_url": "https://x",
    }
    with (
        patch.object(chm, "fetch_latest_master_run", return_value=run),
        patch.object(chm, "_get_last_known_conclusion", return_value="success"),
        patch("agents.systems._telegram.send_telegram") as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = chm.run_ci_health_sweep()

    mock_telegram.assert_not_called()
    mock_vault.assert_not_called()
    assert result == {"ok": True, "state_changed": False, "conclusion": "success"}


def test_run_ci_health_sweep_alerts_on_failure_with_failed_steps():
    run = {
        "ok": True,
        "run_id": 3,
        "conclusion": "failure",
        "head_sha": "abc1234",
        "commit_message": "Break the build\n\nmore detail",
        "html_url": "https://github.com/moh-sudo/AI-EMPIRE/actions/runs/3",
    }
    with (
        patch.object(chm, "fetch_latest_master_run", return_value=run),
        patch.object(chm, "_get_last_known_conclusion", return_value="success"),
        patch.object(chm, "fetch_failed_steps", return_value=["lint-and-test / pytest"]),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = chm.run_ci_health_sweep()

    assert result["ok"] is True
    assert result["state_changed"] is True
    assert result["conclusion"] == "failure"
    assert result["failed_steps"] == ["lint-and-test / pytest"]

    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert "FAILING" in sent_message
    assert "Break the build" in sent_message
    assert "lint-and-test / pytest" in sent_message

    mock_vault.assert_called_once()
    assert mock_vault.call_args.kwargs["action"] == "ci_health_check"
    assert mock_vault.call_args.kwargs["outcome"] == "failure"


def test_run_ci_health_sweep_alerts_on_recovery():
    run = {
        "ok": True,
        "run_id": 4,
        "conclusion": "success",
        "head_sha": "def5678",
        "commit_message": "Fix the build",
        "html_url": "https://x",
    }
    with (
        patch.object(chm, "fetch_latest_master_run", return_value=run),
        patch.object(chm, "_get_last_known_conclusion", return_value="failure"),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = chm.run_ci_health_sweep()

    assert result["state_changed"] is True
    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert "RECOVERED" in sent_message
    mock_vault.assert_called_once()
