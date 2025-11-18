from typing import Dict, Any, List, Literal, Union, Annotated, ClassVar
from pydantic import BaseModel, Field
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
    UPDATE_TODO = 'UPDATE_TODO'
    TERMINATE = 'TERMINATE'
    NO_OP = 'NO_OP'

class BaseAction(BaseModel):
    """Represents a single, executable action proposed by the brain."""
    type: ActionType = Field(frozen=True)
    explanation: str = ""

class NoOpAction(BaseAction):
    """Represents the Reason action."""
    type: Literal[ActionType.NO_OP] = ActionType.NO_OP # type: ignore

class ReasonAction(BaseAction):
    """Represents the Reason action."""
    type: Literal[ActionType.REASON] = ActionType.REASON # type: ignore
    task: str = ""
    files_to_send: List[str] = []
    thoughts_to_send: List[str] = []

class ThinkAction(BaseAction):
    """Represents the Think action."""
    type: Literal[ActionType.THINK] = ActionType.THINK # type: ignore
    delete: bool = False
    label: str = ""
    thought: str = ""

class RunToolAction(BaseAction):
    """Represents the RunTool action."""
    type: Literal[ActionType.RUN_TOOL] = ActionType.RUN_TOOL # type: ignore
    module: str = ""
    tool_class: str = ""
    arguments: Dict[str, Any] = {}

class ToDoType(str, Enum):
    INSERT = 'INSERT'
    APPEND = 'APPEND'
    REMOVE = 'REMOVE'
    NONE = 'NONE'

class UpdateToDoAction(BaseAction):
    """Represents the UpdateToDo action."""
    type: Literal[ActionType.UPDATE_TODO] = ActionType.UPDATE_TODO # type: ignore
    todo_type: ToDoType = ToDoType.NONE
    todo_item: str = ""

class ReadFileAction(BaseAction):
    """Represents the ReadFile action."""
    type: Literal[ActionType.READ_FILE] = ActionType.READ_FILE # type: ignore
    file_path: str = ""

class WriteFileAction(BaseAction):
    """Represents the WriteFile action."""
    type: Literal[ActionType.WRITE_FILE] = ActionType.WRITE_FILE # type: ignore
    file_path: str = ""
    use_thought: str = ""
    contents: str = ""

class DeleteFileAction(BaseAction):
    """Represents the DeleteFile action."""
    type: Literal[ActionType.DELETE_FILE] = ActionType.DELETE_FILE # type: ignore
    file_path: str = ""

class TerminateAction(BaseAction):
    """Represents the Terminate action."""
    type: Literal[ActionType.TERMINATE] = ActionType.TERMINATE # type: ignore

ActionUnion = Union[
    TerminateAction,
    DeleteFileAction,
    WriteFileAction,
    ReadFileAction,
    UpdateToDoAction,
    RunToolAction,
    ThinkAction,
    ReasonAction,
    NoOpAction,
]

Action = Annotated[
    ActionUnion,
    Field(discriminator='type')
]

class Mem(BaseModel):
    """Represents the overall Agent memory."""
    action_queue: List[Action] = []
    counters: Dict[Count, int] = {}
    file_contents: Dict[str, str] = {}
    thoughts: Dict [str, str] = {}
    logs: List[str] = []
    todo: List[str] = []
    last_memorized: str = ""
    deployed_at: str = ""
    is_test: bool = False