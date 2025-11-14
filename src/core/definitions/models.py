from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel
from enum import Enum

class Action_Type(str, Enum):
    REASON = 'REASON'
    READ_FILE = 'READ_FILE'
    WRITE_FILE = 'WRITE_FILE'
    SLUMBER = 'SLUMBER'
    NO_OP = 'NO_OP'

class Count(str, Enum):
    REASONING = 'REASONING'

class Action(BaseModel):
    """Represents a single, executable action proposed by the brain."""
    type: Action_Type = Action_Type.NO_OP
    arguments: Dict[str, Any] = {}
    explanation: str = ""

class Mem(BaseModel):
    """Represents the overall Agent memory."""
    action_queue: List[Action] = []
    counters: Dict[Count, int] = {}
    file_contents: Dict[str, str] = {}
    last_memorized: float = 0