from pydantic import BaseModel

VALID_CLASSIFICATIONS = {"SECRET", "RESTRICTED", "CONFIDENTIAL", "INTERNAL", "PUBLIC"}


class RouteRequest(BaseModel):
    prompt: str
    data_classification: str
    division: str | None = None
    agent_id: str | None = None
    complex_reasoning: bool = False


class RouteResponse(BaseModel):
    routing_destination: str
    model_identifier: str
    sanitization_status: str
    sanitized_prompt: str
