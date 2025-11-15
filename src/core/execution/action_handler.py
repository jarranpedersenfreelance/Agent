from typing import Dict, Any
from core.logger import Logger
from core.definitions.models import Action, ReadFileAction, WriteFileAction, DeleteFileAction
from core.brain.memory import Memory
from core.utilities import read_file, write_file, delete_file

class ActionHandler:
    """Manages the execution of actions other than the REASON action."""
    def __init__(self, constants: Dict[str, Any], logger: Logger, memory: Memory):
        self.constants = constants
        self.logger = logger
        self.memory = memory

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

    def _handle_read_file(self, action: ReadFileAction):
        """Handles the READ_FILE action."""
        file_path = action.arguments.file_path
        self.logger.log_action(action, f"{file_path} - {action.explanation}")

        if not file_path:
            raise ValueError("READ_FILE action requires 'file_path' argument.")
        
        if file_path not in self.memory.memory.file_contents:
            raise ValueError(f"File path '{file_path}' is not tracked in memory.")

        contents = read_file(file_path)
        self.memory.memory.file_contents[file_path] = contents

    def _handle_write_file(self, action: WriteFileAction):
        """Handles the WRITE_FILE action."""
        file_path = action.arguments.file_path
        contents = action.arguments.file_contents
        self.logger.log_action(action, f"{file_path} - {action.explanation}")

        if not file_path:
            raise ValueError("WRITE_FILE action requires 'file_path' argument.")
        
        write_file(file_path, contents)
        self.memory.memory.file_contents[file_path] = contents

    def _handle_delete_file(self, action: DeleteFileAction):
        """Handles the DELETE_FILE action."""
        file_path = action.arguments.file_path
        self.logger.log_action(action, f"{file_path} - {action.explanation}")

        if not file_path:
            raise ValueError("DELETE_FILE action requires 'file_path' argument.")
        
        if file_path not in self.memory.memory.file_contents:
            raise ValueError(f"File path '{file_path}' is not tracked in memory.")
        
        delete_file(file_path)
        del self.memory.memory.file_contents[file_path]