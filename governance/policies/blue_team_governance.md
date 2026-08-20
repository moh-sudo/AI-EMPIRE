# Blue Team Governance (Defense & Security Operations)

**Owner:** Independent Security Testing Function (Blue Team) — not owned by any single
division, mirrors Red Team's own placement in `red_blue_purple_team_vision.md` (Blue
Team sits across the architecture, sibling to Audit and Red Team, not nested inside
Systems & Automation or any other division). The existing agents referenced in Part 1
below **keep their current division ownership** — this document coordinates them under
a shared Blue Team identity, it does not re-org them.
**Authority:** Subordinate to the Constitution, including Law 13 (Security by Design &
Continuous Security Assurance) — same authority chain as
`red_team_rules_of_engagement.md`.
**Written by:** Mohamed + Claude, 2026-08-18, scoped the same session as the Red Team
RoE, per Mohamed's explicit choice to formally adopt the existing scattered defensive
agents under a Blue Team identity *and* scope the one genuinely missing capability
(Part 2) in the same pass, while leaving ownership of the existing agents with their
current divisions rather than transferring it.
**Status:** Part 1 is real today — five agents, live, tested, already running. Part 2's
finding-intake capability is now real too, built 2026-08-18 at
`agents/systems/blue_team_finding_intake.py` (12 tests, live-verified with a real
`audit_vault` write and a real, confirmed-delivered Telegram alert) — see Part 2 below
for exactly what it does and does not do.

## Mission

Detect, prevent, contain, and recover from security incidents affecting AI_EMPIRE —
including receiving and proposing remediations for findings from Red Team exercises
run under `red_team_rules_of_engagement.md`. Blue Team never verifies its own
remediation; Audit does that independently, same separation of duties the Red Team RoE
already establishes for attack findings.

## Part 1 — Existing Blue Team capability (real today, referenced not owned)

Checked against the real codebase before writing this (`ls agents/systems/*.py
agents/audit/*.py`) rather than assumed. Five existing agents are, functionally, Blue
Team work today — detection, hardening, or recovery — just built and governed one at a
time under their own division's pillar, with no shared "Blue Team" identity until now:

| Agent | Real owner (unchanged) | Blue Team category | What it actually does |
|---|---|---|---|
| `agents/systems/reliability_monitor.py` | Systems & Automation (Abdullahi) | Detection + Recovery | Circuit-breaker health checks (5-min sweep), safe auto-restart for stateless services only (n8n, division servers), one-remediation-attempt-per-incident (Rule 4), never restarts data-tier services (Rule 2) or out-of-reach services (Rule 3) |
| `agents/systems/host_security_scan.py` | Systems & Automation (Abdullahi) | Detection | Open-port inventory (`nmap`) and file-level malware scan (`clamscan`) of the real host, via WSL2/Kali; detect-and-propose only |
| `agents/systems/dependency_remediation.py` | Systems & Automation (Abdullahi) | Hardening / Patching | Reads Audit's own CVE findings, proposes specific upgrade versions via Telegram; never runs `pip install` itself |
| `agents/systems/resource_monitor.py` | Systems & Automation (Abdullahi) | Detection | CPU/memory/disk pressure on n8n and the systems server; state-change-only alerting |
| `agents/audit/security_audit.py` | Audit & Verification (Huda) | Secrets Protection + Detection | Hardcoded-secret scanning, `.env`-not-tracked check, git-history secret re-scan, dependency vulnerability scanning (`pip-audit`) |

**Ownership note:** nothing about these agents' code, permissions, database access, or
escalation path changes because of this document. They stay exactly as governed today
in `systems_automation_governance.md` and `security_audit_policy.md`. This section is a
cross-cutting index — Blue Team's governance *references* them so the vision document's
Red/Blue/Audit structure has something real to point to — not a transfer of authority.

## Part 2 — Red Team finding intake & remediation (built 2026-08-18)

This was the literal gap found while scoping the Red Team RoE: none of the five agents
above, nor anything else in the codebase, could receive a Red Team finding and act on
it. The RoE's own pipeline (`RED → Finding → Risk Assessment → BLUE → QA/Security
Verification → AUDIT`) needed this step to actually function end to end. Scoped here
per Rule 10 before any code existed, then built the same session.

**Real, live-verified 2026-08-18:** `agents/systems/blue_team_finding_intake.py`
implements exactly the Can/Cannot list below, no more — `validate_finding()` fails
closed on any missing required field or unrecognized severity (matching the RoE's
evidence and severity schema field-for-field); `receive_finding()` logs the finding to
`audit_vault` unmodified and alerts Mohamed via Telegram; `propose_remediation()`
packages a human-authored fix proposal (never generates one itself), logs it, and
alerts — its `status` field is always `"proposed"`, since the module has no code path
that ever sets `"applied"` or `"verified"`. The Cannot list is enforced by omission:
there is no `apply_fix()`, `mark_verified()`, or `run_test()` function anywhere in the
file — a test (`test_proposal_status_is_never_applied_or_verified`) asserts those
functions don't exist, not just that current behavior looks right. 12 tests passing,
re-verified in a fresh CI-simulation venv before push, and live-verified against real
infrastructure with a clearly-labeled synthetic test finding: two real `audit_vault`
rows written and confirmed by direct query, and a real Telegram message confirmed
delivered (`sent: True`) to the Systems bot.

**Gap closed 2026-08-20: `log_clean_exercise()` added.** Every Red Team exercise
between 2026-08-18 and 2026-08-20 that produced a clean pass (6 of them) had to be
logged via a direct `write_audit_vault()` call instead of through this module, because
`receive_finding()` requires a `severity` and a clean pass has no vulnerability to
classify — flagged repeatedly, finally scoped and closed. `validate_exercise()` reuses
`REQUIRED_FINDING_FIELDS` minus `severity`; `log_clean_exercise()` writes the exact
same `audit_vault` action/outcome (`red_team_exercise_completed` /
`no_vulnerability_found`) every prior manual log already used, so this doesn't rewrite
history, it just gives future exercises a real function to call. 6 new tests (18 total
in the file), live-verified the same way as the original build — a real `audit_vault`
row confirmed by direct query and a real Telegram message confirmed delivered.

### Can

- Receive a classified finding (Critical/High/Medium/Low, per
  `red_team_rules_of_engagement.md`'s severity scale) addressed to Mohamed and Audit.
- Read the finding's full evidence record — exercise ID, target, technique, observed
  behavior, evidence, impact, reproduction conditions, scope, tester, authorization
  reference.
- Propose a specific remediation (a code or config change), matching Dependency
  Remediation's own "detect and propose, never auto-apply" pattern exactly.
- Log every finding received and every remediation proposed to `audit_vault`, same
  pattern every other agent in this project already uses.
- Route the proposed remediation through the same Two-Agent Rule / risk-based approval
  every Systems & Automation capability beyond "restart a known-safe process" already
  requires (`systems_automation_governance.md` Rule 9) — nothing auto-applies.
- Notify Mohamed via Telegram, same as every other agent.

### Cannot

- Auto-apply any remediation. Every fix requires Mohamed's explicit approval before
  it's applied — matches `self_healing_governance.md`'s existing v0.1 status exactly.
- Mark its own remediation as verified or complete. That's QA/Security Verification,
  then Audit's independent verification, per the vision document's own pipeline —
  Blue Team blessing its own fix would violate Law 13 Rule 10 (Security Is Never
  Self-Approved) the same way it would for Red Team self-approving an exercise.
- Modify or suppress the original Red Team finding record.
- Initiate its own adversarial testing to "confirm" a vulnerability exists — that
  stays Red Team's exclusive role per the vision document's Red/Blue separation.
  Retesting a deployed fix is Red Team's job (per the RoE's remediation-retest clause),
  not Blue Team's.

### Escalation

Same Escalation Chain as everything else in this project:
**Abdullahi → Huda → Abdi → Mohamed.** A Blue Team remediation proposal that Huda's
independent verification rejects goes back to Blue Team for revision — never silently
around Audit, never auto-retried without review.

### Placement and status

**Placement resolved 2026-08-18, built the same day:** lives at
`agents/systems/blue_team_finding_intake.py`, nested under Systems & Automation's
existing structure rather than a new top-level `agents/blue_team/` directory.
Reasoning: `agents/systems/server.py` already accumulates several
unrelated-but-adjacent endpoints on one shared server/port/bot (`host_security_scan`,
`ci_health_check`, `resource_check`) — nothing in this project gets dedicated
infrastructure per capability. A new top-level directory would have meant duplicating
an entire division's worth of scaffolding (a new `server.py`, a new Telegram bot and
token, a new port, a new `_memory_helpers.py`/`_telegram.py`) for one file. This
matches the same governance-vs-code-location split already accepted for the five Part 1
agents: code lives wherever's operationally convenient (reusing the existing systems
server on port 8007 and its Telegram bot), while this document stays the authoritative
cross-cutting governance regardless of file path. The known tradeoff, accepted
explicitly: the file path can read as "Blue Team = Systems & Automation" even though
governance says otherwise — same tension already accepted for the five existing
agents, just extended to new code too. Not wired into `server.py` as an HTTP endpoint —
there is no automated trigger source for it yet (Red Team exercises are manual and
conversation-driven per the RoE, not n8n-scheduled), so an unused endpoint would be
scope beyond what's actually needed; called directly as a Python function for now.
Red Team has no equivalent placement question — the RoE bars any autonomous Red Team
agent, so there is no Red Team code to place until a future governance step separately
authorizes one.

## Independence from Red Team

Per the vision document's own principle: if Blue Team knows exactly when and how Red
Team will test, defenses get built for the test rather than for genuine resilience.
Applies even during Red Team's current manual, Claude-run phase — an approved Red Team
exercise is never previewed to whichever existing Blue Team agent monitors the
targeted area before or during the exercise.

## What this document does not do

- Does not transfer ownership of the five Part 1 agents away from Systems & Automation
  or Audit & Verification — see the ownership note above.
- Does not authorize building the Part 2 finding-intake capability — still Rule 10's
  next step, pending Mohamed's go-ahead.
- Does not define Purple Team, which remains vision-only per
  `red_blue_purple_team_vision.md`.
