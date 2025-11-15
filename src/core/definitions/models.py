from typing import Dict, Any, List, Literal
from pydantic import BaseModel
from enum import Enum

class LogType(Enum):
    ERROR = 1
    WARNING = 2
    ACTION = 3
    INFO = 4
    DEBUG = 5

class Count(str, Enum):
    REASON = 'REASON'

class ActionType(str, Enum):
    REASON = 'REASON'
    READ_FILE = 'READ_FILE'
    WRITE_FILE = 'WRITE_FILE'
    DELETE_FILE = 'DELETE_FILE'
    NO_OP = 'NO_OP'

class Action(BaseModel):
    """Represents a single, executable action proposed by the brain."""
    type: ActionType = ActionType.NO_OP
    explanation: str = ""

class Mem(BaseModel):
    """Represents the overall Agent memory."""
    action_queue: List[Action] = []
    counters: Dict[Count, int] = {}
    file_contents: Dict[str, str] = {}
    last_memorized: float = 0

class ReasonActionArgs(BaseModel):
    task: str = ""

class ReasonAction(Action):
    """Represents the Reason action."""
    type = ActionType.REASON
    arguments: ReasonActionArgs = ReasonActionArgs()

class FileArgs(BaseModel):
    file_path: str = ""
    contents: str = ""

class ReadFileAction(Action):
    """Represents the ReadFile action."""
    type = ActionType.READ_FILE
    arguments: FileArgs = FileArgs()

class WriteFileAction(Action):
    """Represents the WriteFile action."""
    type = ActionType.READ_FILE
    arguments: FileArgs = FileArgs()

class DeleteFileAction(Action):
    """Represents the DeleteFile action."""
    type = ActionType.DELETE_FILE
    arguments: FileArgs = FileArgs()
