from typing import Dict, Any, List, Literal, Union
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
    THINK = 'THINK'
    READ_FILE = 'READ_FILE'
    WRITE_FILE = 'WRITE_FILE'
    DELETE_FILE = 'DELETE_FILE'
    RUN_TOOL = 'RUN_TOOL'
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
    thoughts: Dict [str, str] = {}
    last_memorized: float = 0

class ReasonAction(Action):
    """Represents the Reason action."""
    type: Literal[ActionType.REASON] = ActionType.REASON
    task: str = ""

class ThinkAction(Action):
    """Represents the Think action."""
    type: Literal[ActionType.THINK] = ActionType.THINK
    delete: bool = False
    label: str = ""
    thought = ""

class RunToolAction(Action):
    """Represents the RunTool action."""
    type: Literal[ActionType.RUN_TOOL] = ActionType.RUN_TOOL
    module_path: str = ""
    tool_class: str = ""
    arguments: Dict[str, Any] = {}

class ReadFileAction(Action):
    """Represents the ReadFile action."""
    type: Literal[ActionType.READ_FILE] = ActionType.READ_FILE
    file_path: str = ""

class WriteFileAction(Action):
    """Represents the WriteFile action."""
    type: Literal[ActionType.WRITE_FILE] = ActionType.WRITE_FILE
    file_path: str = ""
    contents: str = ""

class DeleteFileAction(Action):
    """Represents the DeleteFile action."""
    type: Literal[ActionType.DELETE_FILE] = ActionType.DELETE_FILE
    file_path: str = ""
