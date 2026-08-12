"""Dependency Vulnerability Remediation Agent -- Systems & Automation,
Security & Performance pillar.

Cooperates with Audit & Verification rather than duplicating it:
Audit's security_audit.py already detects vulnerable dependencies
(passive, read-only, real CVE data via pip-audit) -- this agent calls
that exact same detection function instead of reimplementing pip-audit
invocation, then does the one thing Audit's own design deliberately
doesn't do: propose a specific, actionable fix.

Never applies a fix itself. Upgrading a dependency is "modifying
code" -- falls under this division's own Rule 9 (Two-Agent Rule via
self_healing_governance.md): proposed, never auto-applied, until a
real risk classifier exists. Same pattern Audit's own Bug Detection
module already uses for its proposals.
"""

from packaging.version import InvalidVersion, Version


def scan_for_vulnerabilities() -> dict:
    """Reuses Audit's own detection function rather than
    reimplementing pip-audit invocation -- this IS the cooperation
    mechanism with Audit, not a separate parallel scan."""
    from agents.audit.security_audit import check_dependency_vulnerabilities

    return check_dependency_vulnerabilities()


def propose_remediation(vulnerable_package: dict) -> dict:
    """Pure, testable: turns one vulnerable-package record (matching
    pip-audit's JSON schema -- name, version, vulns[].id,
    vulns[].fix_versions) into a specific, human-readable upgrade
    proposal. Never touches the environment."""
    name = vulnerable_package["name"]
    current_version = vulnerable_package["version"]
    vulns = vulnerable_package.get("vulns", [])

    vuln_ids = [v["id"] for v in vulns]
    fix_version_strs = {fv for v in vulns for fv in v.get("fix_versions", [])}

    recommended_version = None
    if fix_version_strs:
        try:
            recommended_version = str(max(Version(v) for v in fix_version_strs))
        except InvalidVersion:
            # Fall back to whatever pip-audit reported, unsorted,
            # rather than silently dropping the recommendation.
            recommended_version = sorted(fix_version_strs)[-1]

    if recommended_version:
        proposal = (
            f"{name} {current_version} has {len(vuln_ids)} known "
            f"vulnerabilit{'y' if len(vuln_ids) == 1 else 'ies'} "
            f"({', '.join(vuln_ids)}). Recommend upgrading to {recommended_version}."
        )
    else:
        proposal = (
            f"{name} {current_version} has {len(vuln_ids)} known "
            f"vulnerabilit{'y' if len(vuln_ids) == 1 else 'ies'} "
            f"({', '.join(vuln_ids)}) with no fix version published yet -- "
            f"nothing to upgrade to; track for a future release."
        )

    return {
        "package": name,
        "current_version": current_version,
        "vulnerability_ids": vuln_ids,
        "recommended_version": recommended_version,
        "proposal": proposal,
    }


def run_remediation_sweep() -> dict:
    """Full pipeline: scan (via Audit's own detection) -> propose a
    fix for each vulnerable package found -> alert Mohamed via
    Telegram with the proposals (never auto-applied) -> log to
    audit_vault, the same shared table Audit itself reads/writes, so
    Audit has visibility into what Systems found and proposed. Never
    raises -- every step that can fail is caught individually, same
    fail-safe pattern as reliability_monitor.py's sweep."""
    scan = scan_for_vulnerabilities()
    if not scan.get("ok"):
        return {"ok": False, "stage": "scan", "reason": scan.get("reason")}

    vulnerable_packages = scan.get("vulnerable_packages", [])
    if not vulnerable_packages:
        return {"ok": True, "vulnerabilities_found": 0, "proposals": []}

    proposals = [propose_remediation(pkg) for pkg in vulnerable_packages]

    summary = "\n\n".join(p["proposal"] for p in proposals)
    message = (
        f"Dependency Vulnerability Remediation: {len(proposals)} "
        f"package(s) need review.\n\n{summary}\n\n"
        "Nothing has been changed -- these are proposals only, review before upgrading."
    )
    try:
        from agents.systems._telegram import send_telegram

        send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
    except Exception:
        pass  # alert failure never blocks the audit_vault log below

    try:
        from shared.systems_db_connector import write_audit_vault

        write_audit_vault(
            agent_id="systems-dependency-remediation-v0.1",
            division="systems",
            action="dependency_vulnerability_scan",
            outcome="proposals_generated",
            data_classification="INTERNAL",
            law_reference="Systems & Automation Governance -- Security & Performance Pillar",
            metadata={"proposals": proposals},
        )
    except Exception:
        pass  # DB log failure never blocks reporting the real result below

    return {"ok": True, "vulnerabilities_found": len(proposals), "proposals": proposals}
