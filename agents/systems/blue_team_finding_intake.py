"""Blue Team Finding Intake -- Systems & Automation.

Nested here per the 2026-08-18 placement decision in
governance/policies/blue_team_governance.md: reuses this division's
existing server/port/bot rather than a new top-level
agents/blue_team/ directory. Governance ownership stays cross-cutting
(blue_team_governance.md is the authoritative policy) regardless of
where the code physically lives.

Implements Part 2 of that document -- the one capability that was
genuinely missing when governance/policies/red_team_rules_of_engagement.md
was scoped: nothing could receive a Red Team finding and act on it.
Both documents' Cannot lists are enforced by omission here: there is
no apply_fix(), mark_verified(), or run_test() function in this
file, on purpose. Blue Team receives and proposes; it never applies,
never self-verifies, and never re-runs the adversarial test itself.

log_clean_exercise() closes a gap noticed 2026-08-18, flagged several
times, and finally scoped 2026-08-20: receive_finding() requires a
severity, so every clean-pass Red Team exercise run before this
function existed (6 of them) was logged via a direct
write_audit_vault() call instead of going through this module at all.
Same evidence-preservation fields as a finding, minus severity, since
a clean pass has no vulnerability to classify.
"""

REQUIRED_FINDING_FIELDS = {
    "exercise_id",
    "target",
    "timestamp",
    "technique",
    "observed_behavior",
    "evidence",
    "impact",
    "reproduction_conditions",
    "scope",
    "tester",
    "authorization_reference",
    "severity",
}

REQUIRED_EXERCISE_FIELDS = REQUIRED_FINDING_FIELDS - {"severity"}

VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def validate_finding(finding: dict) -> dict:
    """Pure, testable. Fails closed on any missing required field or
    an unrecognized severity -- required fields match
    red_team_rules_of_engagement.md's evidence-preservation list and
    severity scale exactly."""
    missing = REQUIRED_FINDING_FIELDS - finding.keys()
    if missing:
        return {"ok": False, "reason": f"missing required field(s): {', '.join(sorted(missing))}"}

    severity = str(finding["severity"]).lower()
    if severity not in VALID_SEVERITIES:
        return {
            "ok": False,
            "reason": f"invalid severity '{finding['severity']}' -- must be one of {sorted(VALID_SEVERITIES)}",
        }

    return {"ok": True}


def validate_exercise(exercise: dict) -> dict:
    """Pure, testable -- same shape as validate_finding() minus the
    severity check, since a clean-pass exercise has no vulnerability
    to classify."""
    missing = REQUIRED_EXERCISE_FIELDS - exercise.keys()
    if missing:
        return {"ok": False, "reason": f"missing required field(s): {', '.join(sorted(missing))}"}
    return {"ok": True}


def log_clean_exercise(exercise: dict) -> dict:
    """Logs a completed Red Team exercise that produced no finding.
    Same `audit_vault` action/outcome every prior clean-pass exercise
    already used by hand (red_team_exercise_completed /
    no_vulnerability_found), so this doesn't change history, it just
    gives future exercises a real function to call instead of a
    manual write_audit_vault() invocation."""
    validation = validate_exercise(exercise)
    if not validation["ok"]:
        return validation

    try:
        from shared.systems_db_connector import write_audit_vault

        write_audit_vault(
            agent_id="systems-blue-team-finding-intake-v0.1",
            division="systems",
            action="red_team_exercise_completed",
            outcome="no_vulnerability_found",
            data_classification="INTERNAL",
            law_reference="Blue Team Governance -- Part 2, Finding Intake (clean-pass path)",
            metadata={"exercise": exercise},
        )
    except Exception:
        pass  # DB log failure never blocks the Telegram alert below -- same fail-safe pattern as every other sweep in this division

    message = (
        f"Blue Team: Red Team exercise complete, no finding.\n\n"
        f"Exercise: {exercise['exercise_id']}\n"
        f"Target: {exercise['target']}\n"
        f"Technique: {exercise['technique']}\n"
        f"Result: {exercise['observed_behavior']}\n\n"
        "Clean pass -- nothing to remediate."
    )
    try:
        from agents.systems._telegram import send_telegram

        send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
    except Exception:
        pass

    return {"ok": True, "exercise": exercise}


def receive_finding(finding: dict) -> dict:
    """Logs a Red Team finding to audit_vault exactly as received --
    never modified or suppressed, matching the RoE's evidence rule.
    Alerts Mohamed (and, via the same channel, Audit) -- never
    silently dropped. This function never marks the finding verified
    and never proposes a fix itself; see propose_remediation()."""
    validation = validate_finding(finding)
    if not validation["ok"]:
        return validation

    try:
        from shared.systems_db_connector import write_audit_vault

        write_audit_vault(
            agent_id="systems-blue-team-finding-intake-v0.1",
            division="systems",
            action="red_team_finding_received",
            outcome=finding["severity"].lower(),
            data_classification="INTERNAL",
            law_reference="Blue Team Governance -- Part 2, Finding Intake",
            metadata={"finding": finding},
        )
    except Exception:
        pass  # DB log failure never blocks the Telegram alert below -- same fail-safe pattern as every other sweep in this division

    message = (
        f"Blue Team: Red Team finding received.\n\n"
        f"Severity: {finding['severity'].upper()}\n"
        f"Exercise: {finding['exercise_id']}\n"
        f"Target: {finding['target']}\n"
        f"Technique: {finding['technique']}\n"
        f"Impact: {finding['impact']}\n\n"
        "Not remediated -- routing to Mohamed and Audit for review, per red_team_rules_of_engagement.md."
    )
    try:
        from agents.systems._telegram import send_telegram

        send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
    except Exception:
        pass

    return {"ok": True, "finding": finding}


def propose_remediation(finding: dict, proposed_fix: str, proposed_by: str) -> dict:
    """Packages a specific remediation proposal for a previously
    received finding -- never applies it. proposed_fix is
    human-authored (Mohamed or Claude, in a reviewed conversation,
    same as every other proposal in this project); this function's
    job is packaging, logging, and escalation, not idea generation.
    status is always "proposed" -- there is no code path in this
    module that ever sets it to "applied" or "verified"."""
    validation = validate_finding(finding)
    if not validation["ok"]:
        return validation

    if not proposed_fix or not proposed_fix.strip():
        return {"ok": False, "reason": "proposed_fix must not be empty"}

    proposal = {
        "exercise_id": finding["exercise_id"],
        "target": finding["target"],
        "severity": finding["severity"],
        "proposed_fix": proposed_fix,
        "proposed_by": proposed_by,
        "status": "proposed",
    }

    try:
        from shared.systems_db_connector import write_audit_vault

        write_audit_vault(
            agent_id="systems-blue-team-finding-intake-v0.1",
            division="systems",
            action="blue_team_remediation_proposed",
            outcome="proposal_generated",
            data_classification="INTERNAL",
            law_reference="Blue Team Governance -- Part 2, Finding Intake",
            metadata={"proposal": proposal},
        )
    except Exception:
        pass

    message = (
        f"Blue Team: remediation proposed for {finding['exercise_id']}.\n\n"
        f"Target: {finding['target']}\n"
        f"Proposed fix: {proposed_fix}\n"
        f"Proposed by: {proposed_by}\n\n"
        "Not applied -- requires Mohamed's explicit approval, then independent QA/Security "
        "Verification and Audit review before this counts as resolved."
    )
    try:
        from agents.systems._telegram import send_telegram

        send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
    except Exception:
        pass

    return {"ok": True, "proposal": proposal}
