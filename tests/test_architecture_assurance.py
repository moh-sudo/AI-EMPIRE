import json
import sqlite3
from unittest.mock import patch

import pytest

from agents.systems import architecture_assurance as aa


@pytest.fixture
def workflows_dir(tmp_path):
    d = tmp_path / "n8n"
    d.mkdir()
    return d


def _write_workflow(workflows_dir, filename, name, active):
    (workflows_dir / filename).write_text(json.dumps({"name": name, "active": active}), encoding="utf-8")


def _make_n8n_db(tmp_path, rows):
    """rows: list of (name, active, isArchived) tuples."""
    db_path = tmp_path / "database.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE workflow_entity (name TEXT, active BOOLEAN, isArchived BOOLEAN)")
    conn.executemany("INSERT INTO workflow_entity VALUES (?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return db_path


def test_read_declared_workflows_parses_real_files(workflows_dir):
    _write_workflow(workflows_dir, "a.json", "workflow-a", True)
    _write_workflow(workflows_dir, "b.json", "workflow-b", False)

    declared = aa._read_declared_workflows(workflows_dir)

    assert declared == {
        "workflow-a": {"active": True, "file": "a.json"},
        "workflow-b": {"active": False, "file": "b.json"},
    }


def test_read_declared_workflows_skips_unparseable_file(workflows_dir):
    _write_workflow(workflows_dir, "good.json", "workflow-good", True)
    (workflows_dir / "bad.json").write_text("{not valid json", encoding="utf-8")

    declared = aa._read_declared_workflows(workflows_dir)

    assert declared == {"workflow-good": {"active": True, "file": "good.json"}}


def test_read_real_workflows_returns_none_when_db_missing(tmp_path):
    assert aa._read_real_workflows(tmp_path / "does_not_exist.sqlite") is None


def test_read_real_workflows_excludes_archived_rows(tmp_path):
    db_path = _make_n8n_db(
        tmp_path,
        [
            ("audit-agent-daily", 0, 1),  # archived, should be ignored
            ("audit-agent-daily", 1, 0),  # real, non-archived
            ("other-workflow", 0, 0),
        ],
    )

    result = aa._read_real_workflows(db_path)

    assert result["workflows"] == {"audit-agent-daily": True, "other-workflow": False}
    assert result["duplicate_active_names"] == []


def test_read_real_workflows_flags_genuine_duplicate_active_names(tmp_path):
    db_path = _make_n8n_db(
        tmp_path,
        [
            ("weird-workflow", 1, 0),
            ("weird-workflow", 0, 0),  # two non-archived rows, same name -- real anomaly
        ],
    )

    result = aa._read_real_workflows(db_path)

    assert result["duplicate_active_names"] == ["weird-workflow"]


def test_read_real_workflows_is_genuinely_read_only(tmp_path):
    db_path = _make_n8n_db(tmp_path, [("workflow-a", 1, 0)])

    aa._read_real_workflows(db_path)

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT active FROM workflow_entity WHERE name = 'workflow-a'").fetchone()
    conn.close()
    assert row[0] == 1  # untouched


def test_detect_workflow_drift_fails_closed_when_db_missing():
    with patch.object(aa, "_read_real_workflows", return_value=None):
        result = aa.detect_workflow_drift()
    assert result["ok"] is False
    assert "not found" in result["reason"]


def test_detect_workflow_drift_reports_no_findings_when_everything_matches():
    with (
        patch.object(aa, "_read_declared_workflows", return_value={"wf-a": {"active": True, "file": "a.json"}}),
        patch.object(
            aa, "_read_real_workflows", return_value={"workflows": {"wf-a": True}, "duplicate_active_names": []}
        ),
    ):
        result = aa.detect_workflow_drift()
    assert result == {"ok": True, "findings": []}


def test_detect_workflow_drift_reports_active_state_mismatch():
    with (
        patch.object(aa, "_read_declared_workflows", return_value={"wf-a": {"active": False, "file": "a.json"}}),
        patch.object(
            aa, "_read_real_workflows", return_value={"workflows": {"wf-a": True}, "duplicate_active_names": []}
        ),
    ):
        result = aa.detect_workflow_drift()

    assert result["ok"] is True
    assert len(result["findings"]) == 1
    finding = result["findings"][0]
    assert finding["type"] == "active_state_mismatch"
    assert finding["workflow"] == "wf-a"
    assert finding["declared_active"] is False
    assert finding["real_active"] is True


def test_detect_workflow_drift_reports_not_imported():
    with (
        patch.object(aa, "_read_declared_workflows", return_value={"wf-a": {"active": True, "file": "a.json"}}),
        patch.object(aa, "_read_real_workflows", return_value={"workflows": {}, "duplicate_active_names": []}),
    ):
        result = aa.detect_workflow_drift()

    assert result["findings"] == [
        {
            "type": "not_imported",
            "workflow": "wf-a",
            "detail": "declared in a.json but no matching non-archived workflow found in n8n",
        }
    ]


def test_detect_workflow_drift_reports_undocumented_workflow():
    with (
        patch.object(aa, "_read_declared_workflows", return_value={}),
        patch.object(
            aa, "_read_real_workflows", return_value={"workflows": {"mystery-wf": True}, "duplicate_active_names": []}
        ),
    ):
        result = aa.detect_workflow_drift()

    assert result["findings"] == [
        {
            "type": "undocumented_workflow",
            "workflow": "mystery-wf",
            "detail": "running in n8n with no matching infrastructure/n8n/*.json file",
        }
    ]


def test_detect_workflow_drift_reports_duplicate_active_names():
    with (
        patch.object(aa, "_read_declared_workflows", return_value={}),
        patch.object(
            aa,
            "_read_real_workflows",
            return_value={"workflows": {"dupe-wf": True}, "duplicate_active_names": ["dupe-wf"]},
        ),
    ):
        result = aa.detect_workflow_drift()

    assert any(f["type"] == "duplicate_active_workflow_name" for f in result["findings"])


def test_run_architecture_drift_sweep_fails_closed_on_detect_failure():
    with patch.object(aa, "detect_workflow_drift", return_value={"ok": False, "reason": "db not found"}):
        result = aa.run_architecture_drift_sweep()
    assert result == {"ok": False, "stage": "detect", "reason": "db not found"}


def test_run_architecture_drift_sweep_stays_silent_when_clean():
    with patch.object(aa, "detect_workflow_drift", return_value={"ok": True, "findings": []}):
        result = aa.run_architecture_drift_sweep()
    assert result == {"ok": True, "findings_count": 0, "findings": []}


def test_run_architecture_drift_sweep_alerts_and_logs_without_applying_anything():
    findings = [
        {
            "type": "active_state_mismatch",
            "workflow": "wf-a",
            "declared_active": False,
            "real_active": True,
            "detail": "mismatch",
        }
    ]
    with (
        patch.object(aa, "detect_workflow_drift", return_value={"ok": True, "findings": findings}),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = aa.run_architecture_drift_sweep()

    assert result["ok"] is True
    assert result["findings_count"] == 1
    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert "wf-a" in sent_message
    assert "Nothing has been changed" in sent_message
    mock_vault.assert_called_once()
    assert mock_vault.call_args.kwargs["action"] == "architecture_drift_scan"
