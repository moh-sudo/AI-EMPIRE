from typing import Optional

from pydantic import BaseModel

VALID_CLASSIFICATIONS = {"SECRET", "RESTRICTED", "CONFIDENTIAL", "INTERNAL", "PUBLIC"}


class RouteRequest(BaseModel):
    prompt: str
    data_classification: str
    division: Optional[str] = None
    agent_id: Optional[str] = None
    complex_reasoning: bool = False


class RouteResponse(BaseModel):
    routing_destination: str
    model_identifier: str
    sanitization_status: str
    sanitized_prompt: str
