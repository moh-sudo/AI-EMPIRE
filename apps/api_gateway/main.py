import hashlib
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

from .models import RouteRequest, RouteResponse
from .presidio_client import scan_and_sanitize
from .routing import classify_and_route
from .supabase_client import log_audit_incident, log_routing_decision

app = FastAPI(title="AI_EMPIRE Hybrid Router")


@app.post("/api/v1/route", response_model=RouteResponse)
async def route(request: RouteRequest) -> RouteResponse:
    start = time.monotonic()
    prompt_hash = hashlib.sha256(request.prompt.encode()).hexdigest()

    pii_result = scan_and_sanitize(request.prompt)

    decision = classify_and_route(
        data_classification=request.data_classification,
        pii_detected=pii_result.pii_detected,
        sanitized=pii_result.sanitized,
        complex_reasoning=request.complex_reasoning,
    )

    if decision.blocked:
        log_audit_incident(
            agent_id=request.agent_id,
            division=request.division,
            action="route_request",
            outcome="blocked",
            data_classification=request.data_classification,
            severity=2,
            reason=decision.block_reason or "blocked",
        )
        raise HTTPException(status_code=422, detail=decision.block_reason)

    latency_ms = int((time.monotonic() - start) * 1000)

    log_routing_decision(
        prompt_hash=prompt_hash,
        data_classification=request.data_classification,
        routing_destination=decision.destination,
        sanitization_status=pii_result.status,
        model_identifier=decision.model_identifier,
        capability_matched=decision.capability_matched,
        budget_impact=decision.estimated_cost_usd,
        division=request.division,
        agent_id=request.agent_id,
        latency_ms=latency_ms,
    )

    return RouteResponse(
        routing_destination=decision.destination,
        model_identifier=decision.model_identifier,
        sanitization_status=pii_result.status,
        sanitized_prompt=pii_result.sanitized_text,
    )
