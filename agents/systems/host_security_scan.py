"""Host Security Scanning Agent -- Systems & Automation, Security &
Performance pillar.

Scoped in governance/policies/systems_automation_governance.md's "Host
Security Scanning Pillar" section (2026-08-12) BEFORE this file was
written, per Rule 10. Implements exactly that scope, nothing more:

  - nmap: port/listening-service inventory of THIS machine only,
    filling the gap Audit's own security policy already marks
    "not built" -- Audit does secret-scanning and dependency CVEs,
    never a network-facing check.
  - clamscan: file-level malware scan of a given Windows path via
    WSL2's /mnt/c/ mount -- a real second-opinion scan of actual
    files, not the synthetic data the cybersecurity lab (Rule 8)
    uses.

Both tools run inside the existing Kali Linux WSL2 distro. Detect and
propose only, matching dependency_remediation.py's exact pattern:
never installs nmap/clamav itself (Mohamed installs those), never
closes a port, never quarantines or deletes a flagged file. A finding
is a Telegram message and an audit_vault row -- nothing more.

Real, live-verified facts baked into this design (found during
scoping, not assumed): Kali WSL2 ships bare, so a missing tool is a
real, expected outcome handled explicitly rather than crashing.
WSL2 networking here is NAT mode, so nmap must target the Windows
host's real IP through the NAT default gateway to reach the actual
machine -- pointed at anything else, it would only audit the Kali VM.
VMware Workstation running a VM can make WSL2 itself fail to boot
(0x800705B4) -- surfaced as a clear message pointing at the real
cause, not a bare timeout.
"""

import ipaddress
import re
import shlex
import subprocess

WSL_DISTRO = "kali-linux"
_WSL_TIMEOUT = 300
_TOP_PORTS = 100

_VMWARE_HINT = (
    "If this keeps happening, check whether VMware Workstation is running a VM -- "
    "it conflicts with WSL2's Hyper-V platform and can make the whole distro fail to "
    "boot (see governance/policies/systems_automation_governance.md, Host Security "
    "Scanning Pillar)."
)


# wsl.exe's own diagnostic text (VM-creation failures, distro-not-found,
# etc.) is UTF-16LE, unlike everything the guest Linux side prints (real
# UTF-8) -- found live 2026-08-13 when a VMware/WSL2 hypervisor conflict
# resurfaced mid-verification and decoding it as UTF-8 produced garbled
# text with a stray \x00 between every character.
_WSL_NATIVE_ERROR = re.compile(r"Wsl/Service|Error code:\s*Wsl/", re.MULTILINE)


def _decode_wsl_bytes(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    if text.count("\x00") > len(text) / 4:
        text = raw.decode("utf-16-le", errors="replace").lstrip("﻿")
    return text


def _run_in_kali(command: str, timeout: int = _WSL_TIMEOUT, _retried: bool = False) -> dict:
    """Runs a shell command inside the Kali WSL2 distro. ok=False for a
    real invocation failure -- either wsl.exe itself couldn't run at
    all, or it ran but failed to actually reach the distro (VM-creation
    failure, e.g. the VMware/Hyper-V conflict documented in governance;
    this failure mode does NOT raise and does NOT reliably set a
    nonzero returncode, so it's detected by matching wsl.exe's own
    error-message signature instead). A nonzero exit code from the
    *inner* command that did run inside Kali is NOT treated as a
    failure here -- callers (e.g. 'which') rely on nonzero-with-empty-
    output being a normal, meaningful result.

    Retries exactly once (matching this division's "one remediation
    attempt" precedent, e.g. reliability_monitor.py) if the distro
    itself fails to boot -- found live 2026-08-13 that a WSL2 distro
    freshly gone idle ('Stopped') sometimes fails its first boot
    attempt and succeeds immediately on a second, with no VMware VM
    actually running at the time -- a real, observed flakiness in
    this environment, not the VMware conflict this hint otherwise
    points at."""
    try:
        result = subprocess.run(
            ["wsl", "-d", WSL_DISTRO, "--", "bash", "-c", command],
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "reason": "wsl.exe not found -- WSL2 is not installed on this machine."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": f"WSL2 command timed out after {timeout}s. {_VMWARE_HINT}"}
    except subprocess.SubprocessError as e:
        return {"ok": False, "reason": str(e)}

    stdout = _decode_wsl_bytes(result.stdout)
    stderr = _decode_wsl_bytes(result.stderr)
    combined = f"{stdout}{stderr}"
    if _WSL_NATIVE_ERROR.search(combined):
        if not _retried:
            return _run_in_kali(command, timeout=timeout, _retried=True)
        return {
            "ok": False,
            "reason": f"WSL2 failed to reach the {WSL_DISTRO} distro: {combined.strip()} {_VMWARE_HINT}",
        }

    return {"ok": True, "returncode": result.returncode, "stdout": stdout, "stderr": stderr}


def _tool_available(tool: str) -> dict:
    """Honest 'not available' rather than silently skipping -- same
    principle as security_audit.py's pip-audit check. Never installs
    the tool itself; per governance, that's Mohamed's action."""
    result = _run_in_kali(f"which {tool}")
    if not result.get("ok"):
        return result

    path = result["stdout"].strip()
    if not path:
        return {
            "ok": False,
            "reason": (
                f"{tool} is not installed in the {WSL_DISTRO} WSL2 distro. "
                f"Install it yourself with 'sudo apt install {tool}' first -- "
                "this agent never installs tools itself."
            ),
        }
    return {"ok": True, "path": path}


_DEFAULT_ROUTE_GATEWAY = re.compile(r"\bvia\s+(\S+)")


def _host_gateway_ip() -> dict:
    """The Windows host's real IP as seen from inside WSL2's NAT
    network -- the default route's gateway. This is the one address
    that actually reaches the real machine; anything else reachable
    from Kali is the WSL2 VM's own virtual network.

    Parses the raw 'ip route show default' output in Python rather
    than piping through awk -- found live 2026-08-13 that a quoted
    awk program (e.g. \"awk '{print $3}'\") does not reliably survive
    the Python subprocess.run -> wsl.exe -> bash -c boundary: mawk
    silently no-ops and the pipe passes the unprocessed line straight
    through, with no error on either side to signal it. Confirmed with
    a minimal, unambiguous repro (`printf 'a b c' | awk '{print $2}'`
    still returning the whole line). Parsing here, in Python, sidesteps
    that whole class of cross-shell quoting bug entirely -- same reason
    _parse_nmap_open_ports() parses nmap's raw output directly instead
    of asking a shell tool to pre-filter it."""
    result = _run_in_kali("ip route show default")
    if not result.get("ok"):
        return result

    match = _DEFAULT_ROUTE_GATEWAY.search(result["stdout"])
    if not match:
        return {
            "ok": False,
            "reason": f"Could not determine the Windows host's IP -- no default route found inside WSL2 (raw output: {result['stdout'].strip()!r}).",
        }

    ip = match.group(1)
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return {"ok": False, "reason": f"Unexpected default-route output, not a valid IP: {ip!r}"}
    return {"ok": True, "ip": ip}


_NMAP_PORT_LINE = re.compile(r"^(\d+)/(tcp|udp)\s+(\S+)\s+(\S+)")


def _parse_nmap_open_ports(stdout: str) -> list[dict]:
    """Pure, testable: pulls only 'open' ports out of nmap's normal
    (non-JSON) output -- nmap has no JSON format, this is its actual
    output shape."""
    ports = []
    for line in stdout.splitlines():
        match = _NMAP_PORT_LINE.match(line.strip())
        if match and match.group(3) == "open":
            ports.append({"port": int(match.group(1)), "protocol": match.group(2), "service": match.group(4)})
    return ports


def scan_open_ports(target_ip: str | None = None) -> dict:
    """Port/listening-service inventory of this machine. Detect only
    -- never opens or closes anything. target_ip defaults to the
    Windows host's real IP (auto-detected via the WSL2 NAT gateway);
    if a caller passes one explicitly it must be a valid IP address
    (enforced, not just sanitized) -- keeps this to 'this machine
    only' by construction, per the governance scope, and rules out
    shell injection through the target."""
    availability = _tool_available("nmap")
    if not availability.get("ok"):
        return availability

    if target_ip is None:
        gateway = _host_gateway_ip()
        if not gateway.get("ok"):
            return gateway
        target_ip = gateway["ip"]
    else:
        try:
            ipaddress.ip_address(target_ip)
        except ValueError:
            return {"ok": False, "reason": f"target_ip must be a valid IP address, got {target_ip!r}."}

    result = _run_in_kali(f"nmap -sT -Pn --top-ports {_TOP_PORTS} {shlex.quote(target_ip)}", timeout=180)
    if not result.get("ok"):
        return result
    if result["returncode"] != 0:
        return {
            "ok": False,
            "reason": (result["stderr"] or result["stdout"] or f"nmap exited {result['returncode']}").strip()[:500],
        }

    return {"ok": True, "target_ip": target_ip, "open_ports": _parse_nmap_open_ports(result["stdout"])}


def scan_files_for_malware(windows_path: str) -> dict:
    """File-level malware scan of a Windows path, translated to
    WSL2's /mnt/c/ mount. windows_path is relative to C:\\ (e.g.
    'Users/Mohamed amin/Downloads'), forward or back slashes either
    way. Detect only -- never quarantines or deletes a flagged file."""
    availability = _tool_available("clamscan")
    if not availability.get("ok"):
        return availability

    normalized = windows_path.strip().strip("/\\").replace("\\", "/")
    if not normalized or ".." in normalized.split("/"):
        return {"ok": False, "reason": f"Invalid path: {windows_path!r}"}
    wsl_path = f"/mnt/c/{normalized}"

    result = _run_in_kali(f"clamscan -r --infected --no-summary {shlex.quote(wsl_path)}", timeout=600)
    if not result.get("ok"):
        return result
    # clamscan exit codes: 0 = clean, 1 = infected file(s) found, 2 = error.
    if result["returncode"] not in (0, 1):
        reason = (result["stderr"] or result["stdout"]).strip()[:500]
        return {
            "ok": False,
            "reason": reason
            or f"clamscan exited {result['returncode']} -- database may need 'sudo freshclam' run first.",
        }

    infected_files = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
    return {"ok": True, "path_scanned": wsl_path, "infected_files": infected_files}


def run_host_security_sweep(malware_scan_path: str | None = None) -> dict:
    """Full pipeline: port scan (always) + malware scan (only if a
    path is given -- optional in v1, since there's no single 'right'
    default location to scan on Mohamed's machine) -> alert via
    Telegram -> log to audit_vault. Never raises; every step that can
    fail is isolated, same fail-safe pattern as
    dependency_remediation.py's run_remediation_sweep()."""
    ports = scan_open_ports()
    if not ports.get("ok"):
        return {"ok": False, "stage": "port_scan", "reason": ports.get("reason")}

    malware = None
    if malware_scan_path:
        malware = scan_files_for_malware(malware_scan_path)
        if not malware.get("ok"):
            return {"ok": False, "stage": "malware_scan", "reason": malware.get("reason")}

    open_ports = ports["open_ports"]
    infected_files = malware["infected_files"] if malware else []

    lines = [f"Host Security Scan -- {ports['target_ip']}"]
    if open_ports:
        port_list = ", ".join(f"{p['port']}/{p['protocol']} ({p['service']})" for p in open_ports)
        lines.append(f"{len(open_ports)} open port(s): {port_list}")
    else:
        lines.append("No open ports found in the top-100 scan.")

    if malware is not None:
        if infected_files:
            lines.append(
                f"{len(infected_files)} infected file(s) found in {malware['path_scanned']}:\n"
                + "\n".join(infected_files)
            )
        else:
            lines.append(f"No infected files found in {malware['path_scanned']}.")

    lines.append("Nothing has been changed -- these are findings only, review before acting.")
    message = "\n\n".join(lines)

    try:
        from agents.systems._telegram import send_telegram

        send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
    except Exception:
        pass  # alert failure never blocks the audit_vault log below

    try:
        from shared.systems_db_connector import write_audit_vault

        write_audit_vault(
            agent_id="systems-host-security-scan-v0.1",
            division="systems",
            action="host_security_scan",
            outcome="findings_reported",
            data_classification="INTERNAL",
            law_reference="Systems & Automation Governance -- Host Security Scanning Pillar",
            metadata={"open_ports": open_ports, "infected_files": infected_files},
        )
    except Exception:
        pass  # DB log failure never blocks reporting the real result below

    return {
        "ok": True,
        "target_ip": ports["target_ip"],
        "open_ports": open_ports,
        "malware_scan": malware,
    }
