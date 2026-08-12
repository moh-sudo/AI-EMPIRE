from unittest.mock import patch

from agents.systems import dependency_remediation as dr


def test_propose_remediation_picks_the_highest_fix_version():
    pkg = {
        "name": "cryptography",
        "version": "48.0.1",
        "vulns": [
            {"id": "GHSA-aaaa", "fix_versions": ["48.0.3", "48.0.2"]},
            {"id": "GHSA-bbbb", "fix_versions": ["50.0.0"]},
        ],
    }
    result = dr.propose_remediation(pkg)

    assert result["package"] == "cryptography"
    assert result["current_version"] == "48.0.1"
    assert result["vulnerability_ids"] == ["GHSA-aaaa", "GHSA-bbbb"]
    assert result["recommended_version"] == "50.0.0"
    assert "50.0.0" in result["proposal"]
    assert "2 known vulnerabilities" in result["proposal"]


def test_propose_remediation_singular_wording_for_one_vulnerability():
    pkg = {"name": "requests", "version": "2.0.0", "vulns": [{"id": "GHSA-cccc", "fix_versions": ["2.1.0"]}]}
    result = dr.propose_remediation(pkg)
    assert "1 known vulnerability " in result["proposal"] or "1 known vulnerability (" in result["proposal"]


def test_propose_remediation_handles_no_fix_version_published():
    pkg = {"name": "obscure-lib", "version": "1.0.0", "vulns": [{"id": "GHSA-dddd", "fix_versions": []}]}
    result = dr.propose_remediation(pkg)

    assert result["recommended_version"] is None
    assert "no fix version published yet" in result["proposal"]


def test_scan_for_vulnerabilities_delegates_to_audits_own_detection():
    with patch(
        "agents.audit.security_audit.check_dependency_vulnerabilities",
        return_value={"ok": True, "vulnerable_packages": []},
    ) as mock_check:
        result = dr.scan_for_vulnerabilities()

    mock_check.assert_called_once()
    assert result == {"ok": True, "vulnerable_packages": []}


def test_run_remediation_sweep_fails_closed_on_scan_failure():
    with patch.object(dr, "scan_for_vulnerabilities", return_value={"ok": False, "reason": "pip-audit not installed"}):
        result = dr.run_remediation_sweep()

    assert result == {"ok": False, "stage": "scan", "reason": "pip-audit not installed"}


def test_run_remediation_sweep_reports_clean_when_nothing_vulnerable():
    with patch.object(dr, "scan_for_vulnerabilities", return_value={"ok": True, "vulnerable_packages": []}):
        result = dr.run_remediation_sweep()

    assert result == {"ok": True, "vulnerabilities_found": 0, "proposals": []}


def test_run_remediation_sweep_alerts_and_logs_without_applying_anything():
    vulnerable = [
        {"name": "cryptography", "version": "48.0.1", "vulns": [{"id": "GHSA-aaaa", "fix_versions": ["50.0.0"]}]}
    ]
    with (
        patch.object(dr, "scan_for_vulnerabilities", return_value={"ok": True, "vulnerable_packages": vulnerable}),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = dr.run_remediation_sweep()

    assert result["ok"] is True
    assert result["vulnerabilities_found"] == 1
    assert result["proposals"][0]["recommended_version"] == "50.0.0"
    mock_telegram.assert_called_once()
    assert "50.0.0" in mock_telegram.call_args[0][0]
    mock_vault.assert_called_once()
    assert mock_vault.call_args.kwargs["action"] == "dependency_vulnerability_scan"
