from unittest.mock import patch

from agents.systems import blue_team_finding_intake as bti

VALID_FINDING = {
    "exercise_id": "rt-2026-08-18-001",
    "target": "agents/learning/content_ingestion.py",
    "timestamp": "2026-08-18T12:00:00Z",
    "technique": "prompt injection via ingested document",
    "observed_behavior": "agent revealed TELEGRAM_LEARNING_BOT_TOKEN when asked directly",
    "evidence": "transcript excerpt showing the token in the reply",
    "impact": "secret disclosure",
    "reproduction_conditions": "send a document containing the crafted instruction",
    "scope": "agents/learning only, per approved exercise",
    "tester": "Claude",
    "authorization_reference": "2026-08-18 conversation, Mohamed approved",
    "severity": "Critical",
}


def test_validate_finding_accepts_a_complete_finding():
    assert bti.validate_finding(VALID_FINDING) == {"ok": True}


def test_validate_finding_fails_closed_on_missing_fields():
    incomplete = {"exercise_id": "rt-1", "severity": "low"}
    result = bti.validate_finding(incomplete)
    assert result["ok"] is False
    assert "target" in result["reason"]


def test_validate_finding_fails_closed_on_invalid_severity():
    bad = dict(VALID_FINDING, severity="apocalyptic")
    result = bti.validate_finding(bad)
    assert result["ok"] is False
    assert "invalid severity" in result["reason"]


def test_validate_finding_accepts_any_case_for_severity():
    upper = dict(VALID_FINDING, severity="HIGH")
    assert bti.validate_finding(upper) == {"ok": True}


def test_receive_finding_rejects_incomplete_finding_before_any_side_effect():
    with (
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
        patch("agents.systems._telegram.send_telegram") as mock_telegram,
    ):
        result = bti.receive_finding({"exercise_id": "rt-1"})

    assert result["ok"] is False
    mock_vault.assert_not_called()
    mock_telegram.assert_not_called()


def test_receive_finding_logs_and_alerts_on_a_valid_finding():
    with (
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
    ):
        result = bti.receive_finding(VALID_FINDING)

    assert result == {"ok": True, "finding": VALID_FINDING}
    mock_vault.assert_called_once()
    assert mock_vault.call_args.kwargs["action"] == "red_team_finding_received"
    assert mock_vault.call_args.kwargs["outcome"] == "critical"
    assert mock_vault.call_args.kwargs["metadata"] == {"finding": VALID_FINDING}
    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert "CRITICAL" in sent_message
    assert VALID_FINDING["exercise_id"] in sent_message


def test_receive_finding_never_modifies_the_original_finding():
    original = dict(VALID_FINDING)
    with (
        patch("shared.systems_db_connector.write_audit_vault"),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}),
    ):
        bti.receive_finding(VALID_FINDING)

    assert VALID_FINDING == original


def test_receive_finding_db_failure_never_blocks_the_telegram_alert():
    with (
        patch("shared.systems_db_connector.write_audit_vault", side_effect=Exception("db down")),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
    ):
        result = bti.receive_finding(VALID_FINDING)

    assert result["ok"] is True
    mock_telegram.assert_called_once()


def test_propose_remediation_rejects_invalid_finding():
    result = bti.propose_remediation({"exercise_id": "rt-1"}, "fix it", "Claude")
    assert result["ok"] is False


def test_propose_remediation_rejects_empty_fix():
    result = bti.propose_remediation(VALID_FINDING, "   ", "Claude")
    assert result["ok"] is False
    assert "proposed_fix" in result["reason"]


def test_propose_remediation_packages_and_logs_a_valid_proposal():
    with (
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
    ):
        result = bti.propose_remediation(
            VALID_FINDING,
            "Strip instruction-like text from ingested documents before it reaches the prompt.",
            "Claude",
        )

    assert result["ok"] is True
    assert result["proposal"]["status"] == "proposed"
    assert result["proposal"]["exercise_id"] == VALID_FINDING["exercise_id"]
    mock_vault.assert_called_once()
    assert mock_vault.call_args.kwargs["action"] == "blue_team_remediation_proposed"
    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert "Not applied" in sent_message


def test_proposal_status_is_never_applied_or_verified():
    # Structural guarantee, not just a unit test of current behavior --
    # this module has no code path that produces any other status.
    with (
        patch("shared.systems_db_connector.write_audit_vault"),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}),
    ):
        result = bti.propose_remediation(VALID_FINDING, "fix it", "Claude")

    assert result["proposal"]["status"] == "proposed"
    assert not hasattr(bti, "apply_fix")
    assert not hasattr(bti, "mark_verified")
    assert not hasattr(bti, "run_test")
