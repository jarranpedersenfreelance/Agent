from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel
from enum import Enum

class Action_Type(str, Enum):
    REASON = 'REASON'
    SLUMBER = 'SLUMBER'
    NO_OP = 'NO_OP'

class Count(str, Enum):
    REASONING = 'REASONING'

class Action(BaseModel):
    """Represents a single, executable action proposed by the brain."""
    type: Action_Type = Action_Type.NO_OP
    arguments: Dict[str, Any] = {}
    payload: Dict[str, Any] = {}
    success: Optional[bool] = None
    observation: str = ""

class Mem(BaseModel):
    """Represents the overall Agent memory."""
    action_queue: List[Action] = []
    counters: Dict[Count, int] = {}
    last_memorized: float = 0