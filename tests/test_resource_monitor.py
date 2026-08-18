from unittest.mock import MagicMock, patch

from agents.systems import resource_monitor as rm


def test_evaluate_process_reports_not_running():
    assert rm._evaluate_process({"ok": False, "reason": "not running"}) == "not_running"


def test_evaluate_process_reports_ok_under_thresholds():
    result = {"ok": True, "name": "n8n", "memory_mb": 300.0, "cpu_percent": 10.0}
    assert rm._evaluate_process(result) == "ok"


def test_evaluate_process_reports_warning_over_memory_threshold():
    result = {"ok": True, "name": "n8n", "memory_mb": 2000.0, "cpu_percent": 5.0}
    assert rm._evaluate_process(result) == "warning"


def test_evaluate_process_reports_warning_over_cpu_threshold():
    result = {"ok": True, "name": "systems_server", "memory_mb": 50.0, "cpu_percent": 95.0}
    assert rm._evaluate_process(result) == "warning"


def test_evaluate_process_unknown_name_has_no_memory_threshold():
    # threshold_mb defaults to inf for a name not in MEMORY_THRESHOLDS_MB --
    # only CPU can trigger a warning for an untracked process name.
    result = {"ok": True, "name": "unknown_process", "memory_mb": 999999.0, "cpu_percent": 1.0}
    assert rm._evaluate_process(result) == "ok"


def test_evaluate_disk_reports_ok_above_threshold():
    assert rm._evaluate_disk({"free_gb": 74.9}) == "ok"


def test_evaluate_disk_reports_warning_below_threshold():
    assert rm._evaluate_disk({"free_gb": 5.0}) == "warning"


def test_find_pid_on_port_finds_listening_connection():
    conn = MagicMock()
    conn.laddr = MagicMock(port=5678)
    conn.status = psutil_listen_status()
    with patch.object(rm.psutil, "net_connections", return_value=[conn]):
        conn.pid = 1234
        assert rm._find_pid_on_port(5678) == 1234


def test_find_pid_on_port_returns_none_when_not_found():
    with patch.object(rm.psutil, "net_connections", return_value=[]):
        assert rm._find_pid_on_port(5678) is None


def psutil_listen_status():
    import psutil

    return psutil.CONN_LISTEN


def test_check_process_resources_reports_not_running_honestly():
    with patch.object(rm, "_find_pid_on_port", return_value=None):
        result = rm.check_process_resources("n8n", rm.N8N_PORT)
    assert result == {"ok": False, "reason": "n8n is not running (nothing listening on port 5678)."}


def test_check_process_resources_reads_real_process_shape():
    fake_proc = MagicMock()
    fake_proc.memory_info.return_value = MagicMock(rss=300 * 1024 * 1024)
    fake_proc.cpu_percent.return_value = 12.3
    with (
        patch.object(rm, "_find_pid_on_port", return_value=999),
        patch.object(rm.psutil, "Process", return_value=fake_proc),
    ):
        result = rm.check_process_resources("n8n", rm.N8N_PORT)
    assert result == {"ok": True, "name": "n8n", "pid": 999, "memory_mb": 300.0, "cpu_percent": 12.3}


def test_check_disk_free_reads_real_shape():
    fake_usage = MagicMock(free=10 * 1024**3, total=100 * 1024**3)
    with patch.object(rm.shutil, "disk_usage", return_value=fake_usage):
        result = rm.check_disk_free("C:\\")
    assert result == {"ok": True, "path": "C:\\", "free_gb": 10.0, "total_gb": 100.0}


def test_run_resource_check_establishes_baseline_silently_on_first_check():
    with (
        patch.object(
            rm, "check_process_resources", return_value={"ok": True, "name": "x", "memory_mb": 1.0, "cpu_percent": 1.0}
        ),
        patch.object(rm, "check_disk_free", return_value={"ok": True, "free_gb": 50.0}),
        patch.object(rm, "_get_last_known_states", return_value={}),
        patch("agents.systems._telegram.send_telegram") as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = rm.run_resource_check()

    mock_telegram.assert_not_called()
    mock_vault.assert_called_once()
    assert result["changed"] == {}


def test_run_resource_check_does_nothing_when_states_unchanged():
    ok_result = {"ok": True, "name": "x", "memory_mb": 1.0, "cpu_percent": 1.0}
    with (
        patch.object(rm, "check_process_resources", return_value=ok_result),
        patch.object(rm, "check_disk_free", return_value={"ok": True, "free_gb": 50.0}),
        patch.object(rm, "_get_last_known_states", return_value={"n8n": "ok", "systems_server": "ok", "disk": "ok"}),
        patch("agents.systems._telegram.send_telegram") as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = rm.run_resource_check()

    mock_telegram.assert_not_called()
    mock_vault.assert_not_called()
    assert result["changed"] == {}


def test_run_resource_check_alerts_on_a_real_state_change():
    warning_n8n = {"ok": True, "name": "n8n", "memory_mb": 2000.0, "cpu_percent": 5.0}
    ok_server = {"ok": True, "name": "systems_server", "memory_mb": 50.0, "cpu_percent": 5.0}

    def fake_check(name, port):
        return warning_n8n if name == "n8n" else ok_server

    with (
        patch.object(rm, "check_process_resources", side_effect=fake_check),
        patch.object(rm, "check_disk_free", return_value={"ok": True, "free_gb": 50.0}),
        patch.object(rm, "_get_last_known_states", return_value={"n8n": "ok", "systems_server": "ok", "disk": "ok"}),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = rm.run_resource_check()

    assert result["changed"] == {"n8n": "warning"}
    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert "n8n: ok -> warning" in sent_message
    mock_vault.assert_called_once()
    assert mock_vault.call_args.kwargs["action"] == "resource_check"
