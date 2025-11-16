from typing import Dict, Any
from core.logger import Logger
from core.definitions.models import (
    Action, 
    ThinkAction, 
    RunToolAction, 
    ToDoType,
    UpdateToDoAction, 
    ReadFileAction, 
    WriteFileAction, 
    DeleteFileAction
)
from core.brain.memory import Memory
from core.utilities import read_file, write_file, delete_file
from core.execution.toolbox import ToolBox

class ActionHandler:
    """Manages the execution of actions other than the REASON action."""
    def __init__(self, constants: Dict[str, Any], logger: Logger, memory: Memory):
        self.constants = constants
        self.logger = logger
        self.memory = memory
        self.toolbox = ToolBox(constants, self.logger, self.memory)

    def exec_action(self, action: Action):
        """Executes a successfully parsed Action."""
        handle_func = getattr(self, f"_handle_{action.type.name.lower()}", self._handle_unknown)
        handle_func(action)

    def _handle_unknown(self, action: Action):
        """Handles actions that are not recognized."""
        self.logger.log_error(f"Unknown action type: {action.type.name}")

    def _handle_no_op(self, action: Action):
        """Handles the NO_OP action."""
        self.logger.log_action(action, "")

    def _handle_think(self, action: ThinkAction):
        """Handles the THINK action."""
        label = action.label
        thought = action.thought
        is_delete = action.delete
        op_string = 'DELETE' if is_delete else 'INSERT'

        self.logger.log_action(action, f"{op_string} {label} - {action.explanation}")
        thoughts = self.memory.list_thoughts()

        if is_delete:
            if not label in thoughts:
                raise ValueError("THINK action tried to delete thought that doesn't exist.")
            self.memory.remove_thought(label)
        
        else:
            self.memory.set_thought(label, thought)

    def _handle_run_tool(self, action: RunToolAction):
        """Handles the RUN_TOOL action."""
        module = action.module
        tool_class = action.tool_class
        args = action.arguments
        self.logger.log_action(action, f"{tool_class} with args: {str(args)} - {action.explanation}")
        self.toolbox.run_tool(module, tool_class, args)

    def _handle_update_todo(self, action: UpdateToDoAction):
        """Handles the UPDATE_TODO action."""
        if action.todo_type == ToDoType.NONE:
            return
        
        elif action.todo_type == ToDoType.APPEND:
            self.memory.add_todo(action.todo_item)
            self.logger.log_action(action, f"{action.todo_type} {action.todo_item} - {action.explanation}")

        elif action.todo_type == ToDoType.INSERT:
            self.memory.add_immediate_todo(action.todo_item)
            self.logger.log_action(action, f"{action.todo_type} {action.todo_item} - {action.explanation}")

        elif action.todo_type == ToDoType.REMOVE:
            self.memory.remove_todo()
            self.logger.log_action(action, f"{action.todo_type} - {action.explanation}")

    def _handle_read_file(self, action: ReadFileAction):
        """Handles the READ_FILE action."""
        file_path = action.file_path
        mem_files = self.memory.get_filepaths()
        self.logger.log_action(action, f"{file_path} - {action.explanation}")

        if not file_path:
            raise ValueError("READ_FILE action requires 'file_path' argument.")
        
        if file_path not in mem_files:
            raise ValueError(f"File path '{file_path}' is not tracked in memory.")

        contents = read_file(file_path)
        self.memory.fill_file_contents(file_path, contents)

    def _handle_write_file(self, action: WriteFileAction):
        """Handles the WRITE_FILE action."""
        file_path = action.file_path
        contents = action.contents
        self.logger.log_action(action, f"{file_path} - {action.explanation}")

        if not file_path:
            raise ValueError("WRITE_FILE action requires 'file_path' argument.")
        
        if action.use_thought:
            write_file(file_path, self.memory.get_thought(action.use_thought))
        else:
            write_file(file_path, contents)

        self.memory.fill_file_contents(file_path, contents)

    def _handle_delete_file(self, action: DeleteFileAction):
        """Handles the DELETE_FILE action."""
        file_path = action.file_path
        mem_files = self.memory.get_filepaths()
        self.logger.log_action(action, f"{file_path} - {action.explanation}")

        if not file_path:
            raise ValueError("DELETE_FILE action requires 'file_path' argument.")
        
        if file_path not in mem_files:
            raise ValueError(f"File path '{file_path}' is not tracked in memory.")
        
        delete_file(file_path)
        self.memory.remove_file(file_path)