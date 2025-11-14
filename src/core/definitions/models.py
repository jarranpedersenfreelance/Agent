from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum

class Action_Type(Enum):
    REASON = 'REASON'
    SLUMBER = 'SLUMBER'

class Counter(Enum):
    REASONING = 'REASONING'

class Action(BaseModel):
    """Represents a single, executable action proposed by the LLM."""
    type: Action_Type
    arguments: Dict[str, Any] = {}
    payload: Dict[str, Any] = {}
    success: Optional[bool] = None
    observation: str = ""

class Memory(BaseModel):
    """Represents the overall Agent memory."""
    action_queue: List[Action] = []
    counters: Dict[Counter, int] = {}