from unittest.mock import patch

from agents.systems import host_security_scan as hss


def _wsl_ok(returncode=0, stdout="", stderr=""):
    return {"ok": True, "returncode": returncode, "stdout": stdout, "stderr": stderr}


def test_parse_nmap_open_ports_extracts_only_open_ports():
    stdout = (
        "Starting Nmap\n"
        "PORT     STATE    SERVICE\n"
        "22/tcp   open     ssh\n"
        "80/tcp   open     http\n"
        "445/tcp  filtered microsoft-ds\n"
        "Nmap done\n"
    )
    ports = hss._parse_nmap_open_ports(stdout)
    assert ports == [
        {"port": 22, "protocol": "tcp", "service": "ssh"},
        {"port": 80, "protocol": "tcp", "service": "http"},
    ]


def test_parse_nmap_open_ports_handles_no_open_ports():
    assert hss._parse_nmap_open_ports("Starting Nmap\nNmap done: 1 IP address\n") == []


def test_decode_wsl_bytes_handles_normal_utf8_output():
    assert hss._decode_wsl_bytes(b"/usr/bin/nmap\n") == "/usr/bin/nmap\n"


def test_decode_wsl_bytes_recovers_utf16le_error_text():
    # Real bytes captured live 2026-08-13 from a genuine WSL2 VM-creation
    # failure (VMware/Hyper-V conflict) -- wsl.exe writes its own
    # diagnostics in UTF-16LE, unlike the guest's UTF-8 output.
    raw = "This operation returned because the timeout period expired.\n\nError code: Wsl/Service/CreateInstance/CreateVm/0x800705b4\n\n".encode(
        "utf-16-le"
    )
    decoded = hss._decode_wsl_bytes(raw)
    assert "\x00" not in decoded
    assert "Error code: Wsl/Service/CreateInstance/CreateVm/0x800705b4" in decoded


def test_run_in_kali_fails_closed_on_real_vm_creation_failure():
    # Reproduces the exact live failure: wsl.exe returns successfully
    # (no exception) but never reaches the distro, emitting its own
    # UTF-16LE error text instead of running the requested command.
    raw = "Error code: Wsl/Service/CreateInstance/CreateVm/0x800705b4\n".encode("utf-16-le")
    fake_result = type("R", (), {"returncode": 0, "stdout": raw, "stderr": b""})()
    with patch.object(hss.subprocess, "run", return_value=fake_result):
        result = hss._run_in_kali("which nmap")
    assert result["ok"] is False
    assert "WSL2 failed to reach the kali-linux distro" in result["reason"]
    assert "VMware" in result["reason"]


def test_run_in_kali_retries_once_on_transient_boot_failure_then_succeeds():
    failure_raw = "Error code: Wsl/Service/CreateInstance/CreateVm/0x800705b4\n".encode("utf-16-le")
    fail_result = type("R", (), {"returncode": 0, "stdout": failure_raw, "stderr": b""})()
    success_result = type("R", (), {"returncode": 0, "stdout": b"/usr/bin/nmap\n", "stderr": b""})()
    with patch.object(hss.subprocess, "run", side_effect=[fail_result, success_result]) as mock_run:
        result = hss._run_in_kali("which nmap")
    assert result == {"ok": True, "returncode": 0, "stdout": "/usr/bin/nmap\n", "stderr": ""}
    assert mock_run.call_count == 2


def test_run_in_kali_gives_up_after_one_retry():
    failure_raw = "Error code: Wsl/Service/CreateInstance/CreateVm/0x800705b4\n".encode("utf-16-le")
    fail_result = type("R", (), {"returncode": 0, "stdout": failure_raw, "stderr": b""})()
    with patch.object(hss.subprocess, "run", return_value=fail_result) as mock_run:
        result = hss._run_in_kali("which nmap")
    assert result["ok"] is False
    assert mock_run.call_count == 2


def test_tool_available_fails_closed_when_wsl_itself_fails():
    with patch.object(hss, "_run_in_kali", return_value={"ok": False, "reason": "wsl.exe not found"}):
        result = hss._tool_available("nmap")
    assert result == {"ok": False, "reason": "wsl.exe not found"}


def test_tool_available_reports_missing_tool_honestly():
    with patch.object(hss, "_run_in_kali", return_value=_wsl_ok(returncode=1, stdout="")):
        result = hss._tool_available("nmap")
    assert result["ok"] is False
    assert "not installed" in result["reason"]
    assert "apt install nmap" in result["reason"]


def test_tool_available_reports_real_path():
    with patch.object(hss, "_run_in_kali", return_value=_wsl_ok(stdout="/usr/bin/nmap\n")):
        result = hss._tool_available("nmap")
    assert result == {"ok": True, "path": "/usr/bin/nmap"}


def test_host_gateway_ip_rejects_non_ip_via_value():
    with patch.object(hss, "_run_in_kali", return_value=_wsl_ok(stdout="default via not-an-ip dev eth0\n")):
        result = hss._host_gateway_ip()
    assert result["ok"] is False
    assert "not a valid IP" in result["reason"]


def test_host_gateway_ip_handles_missing_default_route():
    with patch.object(hss, "_run_in_kali", return_value=_wsl_ok(stdout="")):
        result = hss._host_gateway_ip()
    assert result["ok"] is False
    assert "no default route found" in result["reason"]


def test_host_gateway_ip_parses_real_route_output():
    # Real output shape captured live 2026-08-13 -- parsed directly in
    # Python rather than piped through awk (see _host_gateway_ip's
    # docstring for why: a quoted awk program doesn't reliably survive
    # the Python -> wsl.exe -> bash -c boundary on this machine).
    with patch.object(
        hss, "_run_in_kali", return_value=_wsl_ok(stdout="default via 172.29.32.1 dev eth0 proto kernel \n")
    ):
        result = hss._host_gateway_ip()
    assert result == {"ok": True, "ip": "172.29.32.1"}


def test_scan_open_ports_fails_closed_when_nmap_missing():
    with patch.object(hss, "_tool_available", return_value={"ok": False, "reason": "nmap is not installed"}):
        result = hss.scan_open_ports()
    assert result == {"ok": False, "reason": "nmap is not installed"}


def test_scan_open_ports_rejects_invalid_explicit_target():
    with patch.object(hss, "_tool_available", return_value={"ok": True, "path": "/usr/bin/nmap"}):
        result = hss.scan_open_ports(target_ip="not-an-ip; rm -rf /")
    assert result["ok"] is False
    assert "valid IP address" in result["reason"]


def test_scan_open_ports_uses_auto_detected_gateway_and_parses_results():
    nmap_output = "PORT   STATE SERVICE\n3389/tcp open  ms-wbt-server\n"
    with (
        patch.object(hss, "_tool_available", return_value={"ok": True, "path": "/usr/bin/nmap"}),
        patch.object(hss, "_host_gateway_ip", return_value={"ok": True, "ip": "172.29.32.1"}),
        patch.object(hss, "_run_in_kali", return_value=_wsl_ok(stdout=nmap_output)) as mock_run,
    ):
        result = hss.scan_open_ports()

    assert result["ok"] is True
    assert result["target_ip"] == "172.29.32.1"
    assert result["open_ports"] == [{"port": 3389, "protocol": "tcp", "service": "ms-wbt-server"}]
    assert "172.29.32.1" in mock_run.call_args[0][0]


def test_scan_files_for_malware_fails_closed_when_clamscan_missing():
    with patch.object(hss, "_tool_available", return_value={"ok": False, "reason": "clamscan is not installed"}):
        result = hss.scan_files_for_malware("Users/Mohamed amin/Downloads")
    assert result == {"ok": False, "reason": "clamscan is not installed"}


def test_scan_files_for_malware_rejects_path_traversal():
    with patch.object(hss, "_tool_available", return_value={"ok": True, "path": "/usr/bin/clamscan"}):
        result = hss.scan_files_for_malware("Users/../Windows/System32")
    assert result["ok"] is False
    assert "Invalid path" in result["reason"]


def test_scan_files_for_malware_reports_clean_scan():
    with (
        patch.object(hss, "_tool_available", return_value={"ok": True, "path": "/usr/bin/clamscan"}),
        patch.object(hss, "_run_in_kali", return_value=_wsl_ok(returncode=0, stdout="")) as mock_run,
    ):
        result = hss.scan_files_for_malware("Users/Mohamed amin/Downloads")

    assert result == {"ok": True, "path_scanned": "/mnt/c/Users/Mohamed amin/Downloads", "infected_files": []}
    assert "/mnt/c/Users/Mohamed amin/Downloads" in mock_run.call_args[0][0]


def test_scan_files_for_malware_reports_infected_files():
    with (
        patch.object(hss, "_tool_available", return_value={"ok": True, "path": "/usr/bin/clamscan"}),
        patch.object(
            hss,
            "_run_in_kali",
            return_value=_wsl_ok(returncode=1, stdout="/mnt/c/Users/foo/evil.exe: Win.Trojan.Generic FOUND\n"),
        ),
    ):
        result = hss.scan_files_for_malware("Users/foo")

    assert result["ok"] is True
    assert result["infected_files"] == ["/mnt/c/Users/foo/evil.exe: Win.Trojan.Generic FOUND"]


def test_scan_files_for_malware_fails_closed_on_real_error():
    with (
        patch.object(hss, "_tool_available", return_value={"ok": True, "path": "/usr/bin/clamscan"}),
        patch.object(hss, "_run_in_kali", return_value=_wsl_ok(returncode=2, stderr="ERROR: Can't open directory")),
    ):
        result = hss.scan_files_for_malware("Users/foo")
    assert result["ok"] is False
    assert "Can't open directory" in result["reason"]


def test_run_host_security_sweep_fails_closed_on_port_scan_failure():
    with patch.object(hss, "scan_open_ports", return_value={"ok": False, "reason": "nmap not installed"}):
        result = hss.run_host_security_sweep()
    assert result == {"ok": False, "stage": "port_scan", "reason": "nmap not installed"}


def test_run_host_security_sweep_fails_closed_on_malware_scan_failure():
    with (
        patch.object(hss, "scan_open_ports", return_value={"ok": True, "target_ip": "172.29.32.1", "open_ports": []}),
        patch.object(hss, "scan_files_for_malware", return_value={"ok": False, "reason": "clamscan not installed"}),
    ):
        result = hss.run_host_security_sweep(malware_scan_path="Users/foo/Downloads")
    assert result == {"ok": False, "stage": "malware_scan", "reason": "clamscan not installed"}


def test_run_host_security_sweep_skips_malware_scan_when_no_path_given():
    with (
        patch.object(hss, "scan_open_ports", return_value={"ok": True, "target_ip": "172.29.32.1", "open_ports": []}),
        patch.object(hss, "scan_files_for_malware") as mock_malware,
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}),
        patch("shared.systems_db_connector.write_audit_vault"),
    ):
        result = hss.run_host_security_sweep()

    mock_malware.assert_not_called()
    assert result["ok"] is True
    assert result["malware_scan"] is None


def test_run_host_security_sweep_alerts_and_logs_without_applying_anything():
    with (
        patch.object(
            hss,
            "scan_open_ports",
            return_value={
                "ok": True,
                "target_ip": "172.29.32.1",
                "open_ports": [{"port": 22, "protocol": "tcp", "service": "ssh"}],
            },
        ),
        patch.object(
            hss,
            "scan_files_for_malware",
            return_value={
                "ok": True,
                "path_scanned": "/mnt/c/Users/foo",
                "infected_files": ["/mnt/c/Users/foo/evil.exe: FOUND"],
            },
        ),
        patch("agents.systems._telegram.send_telegram", return_value={"sent": True}) as mock_telegram,
        patch("shared.systems_db_connector.write_audit_vault") as mock_vault,
    ):
        result = hss.run_host_security_sweep(malware_scan_path="Users/foo")

    assert result["ok"] is True
    assert result["open_ports"] == [{"port": 22, "protocol": "tcp", "service": "ssh"}]
    assert result["malware_scan"]["infected_files"] == ["/mnt/c/Users/foo/evil.exe: FOUND"]
    mock_telegram.assert_called_once()
    sent_message = mock_telegram.call_args[0][0]
    assert "22/tcp" in sent_message
    assert "evil.exe" in sent_message
    assert "Nothing has been changed" in sent_message
    mock_vault.assert_called_once()
    assert mock_vault.call_args.kwargs["action"] == "host_security_scan"
