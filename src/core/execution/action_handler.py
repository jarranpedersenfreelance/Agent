import os
from typing import Dict, Any
from core.definitions.models import Action, Action_Type
from core.brain.memory import Memory
from core.utilities import read_text_file, write_text_file

class ActionHandler:
    """
    Handles the execution of non-reasoning actions like file I/O.
    """

    def __init__(self, constants: Dict[str, Any], memory: Memory):
        self.constants = constants
        self.memory = memory

    def exec_action(self, action: Action) -> str:
        """
        Executes a specific action based on its type.

        Args:
            action: The Action object to execute.

        Returns:
            A string describing the result of the action.
        """
        
        handler = getattr(self, f"_handle_{action.type.name.lower()}", self._handle_unknown)
        return handler(action)

    def _handle_read_file(self, action: Action) -> str:
        """Handles the READ_FILE action."""
        file_path = action.arguments.get('file_path')
        if not file_path:
            raise ValueError("READ_FILE action requires 'file_path' argument.")

        try:
            # Check if file exists in memory's file structure tracking
            if file_path not in self.memory.memory.file_contents:
                return f"ERROR: File path '{file_path}' is not tracked in memory. File may not exist or is ignored."
                
            # 1. Read the file contents from disk
            contents = read_text_file(file_path)

            # 2. Update memory
            self.memory.memory.file_contents[file_path] = contents

            return f"Successfully read file: {file_path}. Content updated in memory."

        except FileNotFoundError:
            return f"ERROR: READ_FILE failed. File not found at path: {file_path}"
        except Exception as e:
            return f"ERROR: An unexpected error occurred during READ_FILE for {file_path}: {e}"

    def _handle_write_file(self, action: Action) -> str:
        """Handles the WRITE_FILE action."""
        file_path = action.arguments.get('file_path')
        contents = action.arguments.get('contents', "")

        if not file_path:
            raise ValueError("WRITE_FILE action requires 'file_path' argument.")

        try:
            # 1. Write the content to disk
            write_text_file(file_path, contents)

            # 2. Update memory's file structure and content
            self.memory.memory.file_contents[file_path] = contents
            
            return f"Successfully wrote to file: {file_path}. Content updated in memory."
            
        except Exception as e:
            return f"ERROR: An unexpected error occurred during WRITE_FILE for {file_path}: {e}"
    
    def _handle_slumber(self, action: Action) -> str:
        """Handles the SLUMBER action (a no-op for now)."""
        return "Agent is slumbing..."

    def _handle_no_op(self, action: Action) -> str:
        """Handles the NO_OP action."""
        return "Performing NO_OP."

    def _handle_unknown(self, action: Action) -> str:
        """Handles actions that are not recognized."""
        return f"ERROR: Unknown action type: {action.type.name}"