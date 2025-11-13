# src/core/models.py

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pydantic import BaseModel 

@dataclass
class Action:
    """Represents a single, executable action proposed by the LLM."""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    success: Optional[bool] = None
    observation: str = ""

@dataclass
class Memory:
    """Represents a single entry in the Agent's long-term memory stream."""
    timestamp: str
    type: str # 'action', 'observation', 'thought', 'plan'
    content: str
    action_id: Optional[str] = None

# Placeholder for the future Pydantic Action model, which is used for reasoning integration
class ReasoningAction(BaseModel):
    """The Pydantic model used for structured output from the LLM."""
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)

# Placeholder for Agent State Models
class RateLimit(BaseModel):
    max_limit: int

class RateLimitState(BaseModel):
    rpm: RateLimit = field(default_factory=lambda: RateLimit(max_limit=1000))
    tpm: RateLimit = field(default_factory=lambda: RateLimit(max_limit=1000000))
    rpd: RateLimit = field(default_factory=lambda: RateLimit(max_limit=10000))
    llm_calls_made: int = 0