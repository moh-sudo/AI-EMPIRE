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
**Status:** Reviewed and confirmed by Mohamed 2026-08-18, since exercised for real —
6 exercises run as of 2026-08-20 (4 scoped-role boundary tests, 1 prompt-injection
test, 1 URL-fetch/SSRF test that found a real vulnerability, since fixed and
independently verified). No autonomous Red Team *agent* exists — see the
standing-approval carve-out below for what has changed since this document was first
written.

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

## Approval process (default: every exercise, no standing authorization)

Matches Law 13 Rule 10 exactly — a Red Team exercise may never self-approve. Before
any exercise not covered by the standing-approval carve-out below:

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
project. The standing-approval carve-out below does not change this: it removes the
per-run approval *conversation*, not the requirement that a human (Mohamed, via an
active session) is the one directing Red Team work in the first place. No cron job,
scheduled trigger, or unattended process may invoke these exercises.

## Standing approval for proven exercise classes (added 2026-08-20)

Mohamed's explicit choice, after weighing three options (standing approval for
already-proven classes / a fixed scheduled regression sweep / a genuinely autonomous
agent that invents new exercises) — this document implements the first, narrowest one.
Two exercise classes have now been run multiple times, always clean, always
read-only/non-destructive by construction, with well-understood blast radius. For these
two specifically, Claude may run a new instance of the same shape **without repeating
the 5-step approval conversation each time** — everything else in this document
(hard exclusions, stop conditions, evidence/reporting, severity classification) still
applies in full, unchanged.

### Class 1 — Scoped-role boundary testing

- **Exact shape:** `get_scoped_client(role).table(table).select("*").execute()` — one
  read-only `SELECT`, nothing else. Any `(role, table)` pair is in scope **except**
  anything Fixera-related (hard exclusion, unconditional) or a table/role pair already
  tested with the identical result on record.
- **Mandatory ground-truth check, every time:** before reporting a result, the same
  table's real row count must be checked via the service-role client (`shared/db.py`'s
  `get_client()`) — a `0`-row scoped result is meaningless without confirming the table
  actually has data the scoped role should have been blocked from seeing. This isn't
  optional shortcut territory; it's what makes the result trustworthy at all (found
  necessary live on 2026-08-18's first exercise).
- **4 exercises of this exact shape already run, all clean** (`personal_habits` x2,
  `rii_watchtowers` x1, and the original disambiguation).

### Class 2 — Prompt injection against an existing LLM call site

- **Exact shape:** call an *already-existing* `chat()`/`generate()`-based function
  directly in Python (never via real Telegram — no real message send, no real bot
  interaction) with text containing an embedded instruction designed to override the
  function's system prompt. Only the **lowest-level pure function** that does not
  persist data or trigger a real external side effect may be called — e.g.
  `generate_flashcards_from_text()`, never `ingest_and_generate()` (which would write a
  real row to `learning_cards`); `answer_question()`, which already has no side effect
  by design.
- **A genuinely new call site (one added to the codebase after this amendment) is not
  automatically in scope** — it hasn't been reviewed for whether a lower-level,
  side-effect-free entry point actually exists, so a first exercise against it still
  needs the full 5-step approval.
- **2 exercises of this exact shape already run, both clean** (Learning's flashcard
  generation, Forex's chat handler).

### What standing approval does not cover

- Any technique not in these two classes — SSRF/URL-fetch testing, secret-disclosure
  beyond Class 2's exact shape, memory-poisoning, multi-agent manipulation, anything
  novel — still needs the full 5-step approval every time. (SSRF specifically produced
  a real finding via URL-fetch testing on 2026-08-20; that class stays exercise-by-exercise
  precisely because it reaches genuinely external state, unlike the two bounded classes
  above.)
- **Any exercise, standing-approved or not, that produces an actual finding (not a
  clean pass) suspends standing approval entirely until Mohamed reviews it.** A finding
  means the exercise revealed something real; the response is to stop, report, and wait
  for direction — never to keep running more standing-approved exercises on the
  assumption the same class is still safe. Reinstating standing approval after a real
  finding is Mohamed's call, not automatic.
- All hard exclusions, stop conditions, evidence-preservation, and severity
  classification rules apply identically whether an exercise was standing-approved or
  individually approved — nothing about reporting or evidence gets lighter-weight.

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
  to Blue Team (`governance/policies/blue_team_governance.md`, real since 2026-08-18)
  via `agents/systems/blue_team_finding_intake.py`'s `receive_finding()`. Red Team may
  subsequently retest the remediation when separately authorized to do so — this
  preserves separation of duties without blocking the Red Team from verifying a fix
  actually worked. Proven end to end 2026-08-20: the SSRF finding above went through
  this exact path, then QA and Audit independently verified the fix.
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
Applies even during manual, Claude-run exercises: a Red Team finding is reported to
Mohamed and Audit through `blue_team_finding_intake.py`, not used to silently pre-brief
whichever agent's defenses it targeted, and Blue Team never learns the exercise was
coming before it ran.

## Escalation

Any finding, or any question about whether something is in scope, follows the existing
Escalation Chain (`systems_automation_governance.md`): **Abdullahi → Huda → Abdi →
Mohamed**, with Huda (Audit) specifically responsible for independently verifying that
an exercise actually followed this RoE, not just that its findings look real.

## What this document does not do

- It does not authorize building a Red Team *agent* — an autonomous process that judges
  what to test next. The standing-approval carve-out above removes a per-run approval
  conversation for two specific, already-proven exercise classes; it does not create
  anything that runs unattended, and Mohamed explicitly chose this narrowest option
  over a scheduled sweep or a genuinely autonomous agent when asked directly. Building
  either of those remains a separate, future scoping step per Rule 10.
- Blue Team's own governance now lives in `governance/policies/blue_team_governance.md`
  — this document no longer needs to say "once scoped" about it.
