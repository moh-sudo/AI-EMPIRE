# Red Team Rules of Engagement (RoE)

**Owner:** Independent Security Testing Function (Red Team) — not owned by any single
division, per `red_blue_purple_team_vision.md`'s structure (Red Team and Blue Team sit
across the architecture, siblings to Audit, not nested inside Systems & Automation or
any other division).
**Authority:** Subordinate to the Constitution, including Law 13 (Security by Design &
Continuous Security Assurance) — specifically Rule 10 ("Security is Never Self-Approved
— a second independent verification is always required") and Rule 9 ("Incident
Escalation — notify Audit, Systems, and Mohamed").
**Written by:** Mohamed + Claude, 2026-08-18, drafted before any Red Team code exists —
matches Rule 10's "new capability scoped in governance before built" precedent already
used for every other agent in this project.
**Status:** Governance only. No Red Team agent or capability exists yet. This document
is the hard prerequisite the vision document itself named as "non-negotiable, not
deferred" — nothing described under "Permitted techniques" below may be exercised,
manually or by an agent, until this document is reviewed and confirmed by Mohamed.

## Purpose

Define the boundaries within which adversarial testing of AI_EMPIRE may occur, so that
Red Team activity strengthens the system rather than becoming a threat itself. Every
exercise must stay inside this document's scope, techniques, and approval process —
no exceptions without Mohamed's explicit, exercise-specific authorization.

## Governance hierarchy

This RoE is not the highest authority in the room. All Red Team activity remains
subordinate to the Constitution, Security Governance, Human Authority, and the specific
exercise's own authorization — in that order. Where two rules conflict, the more
restrictive security boundary always applies, and the exercise must stop pending
clarification rather than proceeding on the more permissive reading. "This RoE allows
it" is never sufficient justification if any other governance layer says otherwise.

## In-scope targets

- AI_EMPIRE's own agents, running locally (`agents/*/`), including their Telegram bot
  interfaces, `_memory_helpers.py` read/write paths, and inter-agent routing logic.
- AI_EMPIRE's own Supabase tables reachable via the scoped RLS+JWT clients
  (`shared/scoped_db.py`) — testing whether a scoped role can be tricked into acting
  outside its own division's tables, for example.
- n8n workflows that call AI_EMPIRE's own FastAPI servers (`agents/*/server.py`).
- Governance enforcement itself — Approval Matrix gates, HITL confirmation flags,
  Constitutional-rule checks in code — specifically *because* these are exactly what a
  real attacker would target first.

## Hard exclusions — never in scope, no exception process

- **Fixera** (`C:\fixera`) — a separate, real production platform with real customers
  and its own database. Already governed as permanently separate
  (`ai-empire-fixera-separation` decision). Never a Red Team target, full stop — not
  even read-only reconnaissance, since Fixera is reached only via a scoped read-only
  connector that itself should not be probed adversarially without Fixera's own
  security process being involved, which is out of scope for this document entirely.
- **Any live-funded MT5 account.** Forex's Entry & Exit capability is demo-only today;
  if that ever changes, real-money execution stays permanently excluded from Red Team
  testing regardless.
- **Real external sends** — no exercise may cause an actual Telegram message to go to
  a real recipient outside the test's own control, no actual email send, no actual
  post to any public surface. If a technique's realistic form requires "does the agent
  actually send X," the exercise stops at "the agent decided to send X" and confirms
  that decision was captured, never lets the send itself execute.
- **Destructive actions** — no exercise may delete real data, drop tables, alter
  production configuration, or take any action that Systems & Automation's own
  governance already restricts (Database Governance Rule 2: no agent, Red Team
  included, ever runs a migration or destructive query against production).
- **Denial of service** — no exercise may degrade availability of any real, currently
  running service (division servers, n8n, Supabase, Ollama).
- **The Juice Shop practice lab is a separate thing entirely.** Practicing offensive
  technique against Juice Shop (`agents/systems` Tools & Internal Systems pillar) is
  not "Red Team" in this document's sense — Juice Shop is a synthetic, air-gapped
  target for skill-building. This RoE governs testing against AI_EMPIRE's *own real*
  agents and infrastructure specifically.

## Permitted techniques (once this RoE is confirmed)

Scoped to the AI-specific categories named in the vision document, always in
**detect-and-report mode only** — an exercise proves a weakness exists, it never
exploits it further than the minimum needed to prove it:

- Prompt injection via crafted Telegram messages, ingested documents, or research
  content, testing whether an agent takes an unauthorized action or reveals
  restricted information.
- Attempts to get an agent to bypass its own Approval Matrix / HITL gate.
- Attempts to get an agent to reveal a secret (API key, token) via conversation.
- Memory-poisoning attempts — inserting crafted data into `memory_experience` /
  `memory_knowledge` and checking whether a later, unrelated agent decision is
  influenced by it inappropriately.
- Multi-agent manipulation — checking whether one agent's output, when routed to
  another agent, can cause the second agent to act outside its own authority.
- Scoped-role boundary testing — checking whether a division's RLS+JWT scoped client
  can read or write another division's tables.

## Prohibited techniques

Anything not explicitly listed above requires a fresh, written scope extension
approved by Mohamed before use — this list is intentionally not exhaustive, the
default is "not permitted unless named."

## Approval process (every exercise, no standing authorization)

Matches Law 13 Rule 10 exactly — a Red Team exercise may never self-approve. Before
any exercise:

1. State the specific target (which agent, which table, which workflow).
2. State the specific technique from the "Permitted techniques" list above.
3. State the start/end time or trigger condition for the exercise.
4. State the stop condition (see below).
5. Get Mohamed's explicit go-ahead for that specific exercise, in that conversation —
   never inferred from a prior approval, never a standing "you can always test X."

**No autonomous Red Team agent exists or is authorized by this document.** Until a
dedicated agent is separately scoped and reviewed (a future governance step, not this
one), Red Team exercises are run manually, by Claude, only when Mohamed directs a
specific exercise live — the same "no autonomous freelancing in a high-risk category"
posture already applied to Bug Detection's `propose_fix()` and every migration in this
project.

## Minimum necessary access

Even once an exercise is authorized, Red Team receives only the minimum credentials,
permissions, data, and access necessary to conduct that specific exercise — never a
standing broad-access account, never more than the one target named in the approval.
Matches Law 13 Rule 4 (Principle of Least Privilege) directly, applied to testing
access the same way it already applies to every agent's operational access.

## Immediate stop rule — the single most important rule in this document

If an exercise unexpectedly reaches an excluded system, sensitive production data, an
unauthorized account, an external recipient, or any condition outside the approved
scope, **testing must immediately stop.** Not "wrap up the current step first," not
"just confirm what happened" — stop the instant the condition is recognized. The
tester must then preserve whatever evidence already exists and report the scope
breach to Mohamed directly, matching Law 13 Rule 9's incident-escalation requirement.

Concretely, halt immediately if any of these occur:

- The exercise reaches or appears about to reach Fixera, a live-funded account, or any
  other hard exclusion above.
- A real external message, email, or post is about to be sent (not simulated).
- Any real data would be deleted, altered, or made unrecoverable.
- Any currently-running service's availability is degraded.
- The exercise's actual behavior diverges from what was approved in the approval
  process above.
- Any sensitive production data is unexpectedly encountered, even if the target itself
  was correctly in scope (e.g. a scoped-role boundary test unexpectedly surfaces real
  customer-adjacent data it shouldn't have reached).

## Evidence and reporting

- Every exercise, successful or not, gets a real `audit_vault` row (same pattern every
  other agent in this project already uses) and a real finding reported to Mohamed —
  never silently dropped, never summarized away.
- Each finding preserves, at minimum: exercise ID, target, timestamp, technique used,
  observed behavior, evidence, impact, reproduction conditions, scope, tester, and the
  authorization reference (which approved-exercise conversation authorized it).
- The Red Team does not remediate or approve its own findings. Remediation is assigned
  to the appropriate defensive or engineering function (Blue Team, once scoped, or
  whichever agent/person owns the affected system). Red Team may subsequently retest
  the remediation when separately authorized to do so — this preserves separation of
  duties without blocking the Red Team from verifying a fix actually worked.
- No evidence may be altered or deleted once recorded, including to "clean up" a test —
  mirrors Law 13 Rule 6 ("Security Audit Cannot Be Disabled... no agent may suppress
  alerts or modify audit evidence"), applied here to Red Team's own findings.

## Severity classification

Every finding gets classified before it's reported, so Mohamed and Audit can triage
without the Red Team implicitly deciding final incident severity itself:

- **Critical** — Constitutional/security boundary bypass, unauthorized sensitive-data
  access, or privilege escalation to a highly privileged control.
- **High** — meaningful authentication/authorization bypass, significant agent/tool
  privilege abuse.
- **Medium** — a limited control weakness with constrained impact.
- **Low** — a minor weakness or defense-in-depth gap.

No dedicated Risk Assessment function exists in this codebase yet (checked before
writing this — nothing under `agents/` or `governance/` implements one). Until one is
separately scoped, a classified finding routes straight to Mohamed and Audit (Huda) for
triage, rather than referencing a Risk Assessment step that doesn't exist yet.

## Cleanup requirement

If a permitted exercise creates temporary test artifacts (a test account, a test file,
a test row in a table), the sequence is always: **Test → Preserve Evidence → Safe
Cleanup → Verify Cleanup → Report.** Cleanup happens only *after* evidence is preserved,
never before, and never in a way that touches or removes the evidence itself. If
cleanup can't be done safely without risking real data, it is documented separately and
flagged to Mohamed rather than attempted.

## Independence from Blue Team

Per the vision document's own principle: if Blue Team knows exactly when and how Red
Team will test, defenses get built for the test rather than for genuine resilience.
Until Blue Team is itself scoped, this is a placeholder rule — but the intent holds
even during manual, Claude-run exercises: a Red Team finding is reported to Mohamed
and Audit, not used to silently pre-brief whichever agent's defenses it targeted.

## Escalation

Any finding, or any question about whether something is in scope, follows the existing
Escalation Chain (`systems_automation_governance.md`): **Abdullahi → Huda → Abdi →
Mohamed**, with Huda (Audit) specifically responsible for independently verifying that
an exercise actually followed this RoE, not just that its findings look real.

## What this document does not do

- It does not authorize building a Red Team agent. That's a separate, future scoping
  step, per Rule 10, once Mohamed decides to move from "manual, approved-per-exercise"
  to something more automated.
- It says nothing about Blue Team, which needs its own governance document before any
  Blue Team capability is built either.
