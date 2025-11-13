# src/core/action_handler.py
import os 
from .models import Action
from .utilities import read_text_file, write_text_file, delete_file, sanitize_filename

class ActionHandler:
    # BUG 1 FIX: Updated signature to accept all managers and constants.
    def __init__(self, constants, memory_manager, resource_manager, task_manager):
        """Initializes the Action Handler with core components."""
        self.constants = constants
        self.memory_manager = memory_manager
        self.resource_manager = resource_manager
        self.task_manager = task_manager
        # Base directory for all file operations (set to CWD, which is /app/workspace in the container)
        self.base_dir = os.path.abspath(os.getcwd()) # Use abspath for consistency

    def execute_action(self, action: Action) -> str:
        """
        Executes the requested action and returns a text result.
        """
        action_type = action.action.upper()
        
        if action_type == "READ_FILE":
            return self.handle_read_file(action)
        # TODO: Add other action handlers here (WRITE_FILE, DELETE_FILE, etc.)
        
        return f"Error: Unknown action type '{action_type}'. Please specify a valid action from the action_syntax.txt file."

    def _resolve_path(self, file_path: str) -> str:
        """
        FIX: Issue 9 - Resolves the file path relative to the agent's base directory.
        """
        # Ensure the path is relative to the base directory, then resolve it to an absolute path
        # Note: os.path.join handles absolute paths in file_path correctly by ignoring base_dir
        # but we need to ensure the final path is consistently prefixed if it's relative.
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
            
        return file_path


    def handle_read_file(self, action: Action) -> str:
        """
        Handles the READ_FILE action.
        """
        file_path_raw = action.parameters.get('file_path')
        if not file_path_raw:
            return "Error: READ_FILE requires 'file_path' parameter."

        # FIX: Use internal path resolver (Issue 9)
        file_path = self._resolve_path(file_path_raw)

        # The ResourceManager handles path safety checks (Issue 4)
        if not self.resource_manager.is_file_path_safe(file_path):
            return f"Error: File path '{file_path_raw}' is unsafe or outside the allowed scope."

        try:
            content = read_text_file(file_path)
            
            # Record in memory (Issue 5)
            self.memory_manager.update_read_files(file_path_raw, content) # Save the raw path for cleaner memory context
            
            return f"File content:\n--- {file_path_raw} ---\n{content}\n---"
        except FileNotFoundError:
            return f"Error: File '{file_path_raw}' not found."
        except Exception as e:
            return f"Error: Failed to read file '{file_path_raw}': {e}"

    # TODO: Other action handler methods (e.g., handle_write_file, handle_delete_file) would be here