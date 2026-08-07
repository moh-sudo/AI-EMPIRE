from dataclasses import dataclass

from .models import VALID_CLASSIFICATIONS

LOCAL_MODEL = "ollama/llama3-8b"
CLOUD_MODEL = "claude-sonnet-5"


@dataclass
class RoutingDecision:
    destination: str  # "local" | "cloud" | "none"
    model_identifier: str
    capability_matched: str | None
    estimated_cost_usd: float
    blocked: bool = False
    block_reason: str | None = None


def classify_and_route(
    data_classification: str,
    pii_detected: bool,
    sanitized: bool,
    complex_reasoning: bool,
) -> RoutingDecision:
    """Implements CONTEXT.md's Routing Rules. SECRET never reaches cloud.
    RESTRICTED/CONFIDENTIAL with unsanitized PII are blocked outright rather
    than silently downgraded to local — the caller decides what to do next.
    """
    classification = data_classification.upper()
    if classification not in VALID_CLASSIFICATIONS:
        return RoutingDecision(
            "none",
            "none",
            None,
            0.0,
            blocked=True,
            block_reason=f"Unknown data_classification '{data_classification}'",
        )

    if classification == "SECRET":
        return RoutingDecision("local", LOCAL_MODEL, "secret_local_only", 0.0)

    if classification == "RESTRICTED":
        if pii_detected and not sanitized:
            return RoutingDecision(
                "none",
                "none",
                None,
                0.0,
                blocked=True,
                block_reason="RESTRICTED data contains unsanitized PII; cloud routing is prohibited and local fallback requires explicit sanitization first.",
            )
        return RoutingDecision("local", LOCAL_MODEL, "restricted_local_default", 0.0)

    if classification == "CONFIDENTIAL":
        if pii_detected and not sanitized:
            return RoutingDecision(
                "none",
                "none",
                None,
                0.0,
                blocked=True,
                block_reason="CONFIDENTIAL data contains PII that Presidio failed to sanitize; request blocked, Severity 2 incident logged.",
            )
        if complex_reasoning and sanitized:
            return RoutingDecision("cloud", CLOUD_MODEL, "confidential_cloud_sanitized", 0.003)
        return RoutingDecision("local", LOCAL_MODEL, "confidential_local_default", 0.0)

    if classification == "INTERNAL":
        return RoutingDecision("local", LOCAL_MODEL, "internal_local_default", 0.0)

    # PUBLIC
    return RoutingDecision("local", LOCAL_MODEL, "public_default_local", 0.0)
