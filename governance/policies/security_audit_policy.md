# Security Audit Policy

**Owner:** Audit & Verification Division (Security Audit Agent)
**Authority:** Subordinate to the Constitution, including Law 13 (Security by Design & Continuous Security Assurance).
**Written by:** Mohamed, 2026-08-03.

## Mission

Continuously verify that the security architecture, controls, infrastructure, agents, and integrations remain compliant with the Constitution and Security Governance.

## Full check categories (as specified)

- **Infrastructure:** servers, firewalls, VPNs, ports, certificates
- **AI:** prompt injection, jailbreak attempts, hallucination risks, agent permissions, tool permissions
- **Identity:** authentication, RBAC, MFA, temporary access, expired accounts
- **Secrets:** API keys, tokens, certificates, environment variables
- **Supply Chain:** dependencies, Docker images, third-party APIs, open-source packages
- **Database:** encryption, backups, access logs, Row-Level Security (RLS)
- **Application:** XSS, SQL injection, CSRF, SSRF, command injection, file-upload security
- **AI Governance:** Constitutional compliance, Approval Matrix, HITL, agent permissions, autonomous actions

## Current implementation status (v0.1, 2026-08-03)

AI_EMPIRE today is a single-developer, locally-run system (n8n + Python servers on one Windows machine, one Mac for local models) — not a multi-server cloud deployment with its own IAM/RBAC/MFA stack, and it doesn't run a public-facing web application of its own (Fixera's actual customer-facing apps are a separate codebase, `C:\fixera`, with their own security posture). Given that real shape, v0.1 honestly covers only the categories that actually apply and are realistically checkable today:

- ✅ **Secrets** — real: scans the repo for hardcoded secret patterns, confirms `.env` isn't tracked by git, and (added 2026-08-18) scans the full commit history (`git log -p`, added lines only) for the same patterns — catches a secret later removed from the live code but still retrievable in an old commit. Live-verified against this repo's real 90-commit history: clean, 0 findings, ~3 seconds (`agents/audit/security_audit.py`)
- ✅ **Supply Chain** — real: dependency vulnerability scanning via `pip-audit` against `requirements.txt`
- 🟡 **AI Governance** — partial, pre-existing: the original 4 governance checks (`agents/audit/checks.py`) cover data-routing sanitization and stale agent reviews; Approval Matrix / HITL enforcement isn't independently audited, it's just enforced structurally in each agent's own code (confirmed=True gates, etc.)
- ❌ **Identity** — genuinely not applicable to the current single-machine, single-user setup; nothing to build yet.
- 🟡 **Database (RLS specifically)** and 🟡 **AI (prompt injection/jailbreak/hallucination)** — not automated, but real empirical evidence now exists via manual, RoE-governed Red Team exercises (`governance/policies/red_team_rules_of_engagement.md`), not this agent's own continuous scanning: 4 scoped-role RLS boundary tests (all clean, ground-truth verified against the service-role client each time) and 2 prompt-injection/secret-disclosure exercises (both clean). Genuine coverage, just human-triggered per exercise rather than continuous.
- ⚠️ **Application: SSRF specifically — a real, corrected finding, 2026-08-20.** This category's original ❌ reasoning ("doesn't run a public-facing web application") was checked against real code rather than trusted as still accurate 17 days later, and it didn't hold: `agents/learning/content_transform.py`'s `extract_text_from_url()`, reachable via Learning's own Telegram `URL:` ingest command, had zero validation and could reach internal-only endpoints (confirmed live: pulled a real 2630-byte response from `127.0.0.1:8007/openapi.json`). A non-public-facing system can still have an SSRF-shaped input path if it ingests attacker-influenced URLs. Found via a Red Team exercise, routed through `blue_team_finding_intake.py` for real (its first non-clean-pass finding), classified High, and fixed with Mohamed's explicit approval — `_is_safe_url()` now rejects non-http(s) schemes and any resolved private/loopback/link-local/reserved/multicast address before fetching, live-verified against the real exploit (now blocked) and a real public URL (still works). **The lesson generalized, not just patched:** the other four categories left as ❌ or 🟡 above were re-checked, not assumed, before writing this update — XSS/SQLi/CSRF/command-injection/file-upload genuinely have no equivalent surface right now (no template rendering, no SQL string-building, no session/cookie auth, no arbitrary file execution path found), so they stay ❌, honestly, not because they weren't looked at.
- ❌ **Infrastructure (beyond what Host Security Scanning already covers)** — `agents/systems/host_security_scan.py` (Systems & Automation, not this agent) already does real `nmap` port/service inventory and `clamscan` malware scanning of this host, daily via login trigger. Genuine partial coverage exists in the system; it's just owned by a different division's pillar, not this policy's own agent. Nothing beyond that (firewalls, certificates) applies to the current single-machine setup.

This policy is written for the system AI_EMPIRE is meant to become, not just what exists today — as real infrastructure, identity management, and public-facing surfaces get added, the corresponding categories above should move from ❌ to real, verified coverage.
