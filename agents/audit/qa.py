"""Quality Assurance -- Audit & Verification Division.

General-purpose review of another agent's output -- accuracy,
completeness, hallucination, consistency, formatting, business-logic
soundness (Mohamed's own definition, 2026-08-03). Real Ollama judgment,
his explicit choice, same reasoning as research/diagnosis: this is a
judgment call a deterministic rule can't make.

First real wiring: reviews Bug Detection's root-cause diagnoses before
they reach Mohamed, implementing the Self-Healing Governance Policy's
Two-Agent Rule (Systems Agent -> QA Agent -> Compliance Agent ->
Deploy) -- Mohamed's own explicit request, so a single agent is never
developer, reviewer, and deployer at once. Written generically
(review_output()) so it's reusable for other divisions' outputs later,
not hardcoded to bug diagnoses only.
"""

QA_SYSTEM_PROMPT = (
    "You are a QA reviewer checking another AI agent's output before it reaches "
    "a human for approval. You are given the original context/evidence and the "
    "agent's output. Check for: (1) does the output actually follow from the "
    "evidence given, or does it hallucinate claims not supported by it, (2) is "
    "it complete -- does it actually answer what was asked, (3) is it internally "
    "consistent, (4) is it clearly formatted. Respond in exactly this format:\n"
    "VERDICT: PASS or FAIL\n"
    'CONCERNS: <list any real issues, or "none" if it passes cleanly>'
)


def _parse_qa_response(reply: str) -> dict:
    lines = reply.strip().splitlines()
    verdict = "FAIL"  # fail closed if parsing fails -- never silently pass on a malformed QA response
    concerns = reply

    for line in lines:
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
        elif line.upper().startswith("CONCERNS:"):
            concerns = line.split(":", 1)[1].strip()

    return {"passed": verdict == "PASS", "concerns": concerns}


def review_output(context: str, output: str) -> dict:
    """Real Ollama-based review. Never raises -- if the model call
    itself fails, fails closed (passed=False) rather than assuming
    the output is fine."""
    from shared.models.ollama_client import chat as ollama_chat

    prompt = f"ORIGINAL CONTEXT/EVIDENCE:\n{context}\n\nAGENT OUTPUT TO REVIEW:\n{output}"
    result = ollama_chat(prompt, system=QA_SYSTEM_PROMPT)

    if not result.get("ok"):
        return {"passed": False, "concerns": f"QA review itself failed: {result.get('reason')}"}

    return _parse_qa_response(result["reply"])
