# src/core/models.py
from pydantic import BaseModel, Field
import time
from typing import Dict, List, Any # FIX: Added typing imports

# --- Pydantic Schemas for Gemini API (Issue 6) ---
ACTION_QUEUE_SCHEMA = {
    "type": "array",
    "description": "A list of one or more actions to be executed in sequence. If no action is needed, return an empty list.",
    "items": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The name of the action to take (e.g., 'read_file', 'write_file', 'exit_and_finish', 'agent_set_goals', 'execute_code')."
            },
            "parameters": {
                "type": "object",
                "description": "A dictionary of parameters required by the action. If no parameters are needed, this should be an empty object."
            }
        },
        "required": ["action", "parameters"]
    }
}

# --- Core Agent Models ---

# New Resource State Model (Issue 5)
class RateLimit(BaseModel):
    """Represents a single rate limit counter with a timestamp for reset checks."""
    count: int = 0
    max_limit: int
    last_reset_timestamp: float = Field(default_factory=time.time)

class ResourceState(BaseModel):
    """The persistent state for tracking LLM API usage."""
    # max_limit is set upon loading from constants
    rpm: RateLimit = Field(default_factory=lambda: RateLimit(max_limit=1))
    tpm: RateLimit = Field(default_factory=lambda: RateLimit(max_limit=1))
    rpd: RateLimit = Field(default_factory=lambda: RateLimit(max_limit=1))
    llm_calls_made: int = 0

class MemoryStream(BaseModel):
    """The persistent state for the agent's memory."""
    # FIX: Issue 7 - Added context_history for LLM interactions
    context_history: List[Dict[str, str]] = Field(default_factory=list)
    read_files: Dict[str, str] = Field(default_factory=dict)
    development_plan: str = "Determine best next step of growth based on current goals, codebase, and resources. Self-Update to achieve this growth, and then iterate."
    known_files: List[str] = Field(default_factory=list)

class Action(BaseModel):
    """Represents a single action requested by the LLM."""
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)