# src/core/action_handler.py
import os
from typing import Any, Dict
from pydantic import ValidationError
from .models import Action # FIX: Changed from src.core.models to relative import
from .utilities import read_text_file, write_text_file, delete_file # FIX: Changed from src.core.utilities to relative import
# NOTE: TaskManager, ResourceManager, MemoryManager are passed via __init__

# --- Action Handler ---

class ActionHandler:
    """
    Handles the execution of recognized agent actions.
    Coordinates between managers (Resource, Memory, Task).
    """
    
    def __init__(self, constants: Dict[str, Any], memory_manager: Any, resource_manager: Any, task_manager: Any):
        self.constants = constants
        self.memory = memory_manager
        self.resources = resource_manager
        self.task = task_manager
        # Assume base_dir is the root execution path where 'workspace' resides
        self.base_dir = os.path.abspath(os.getcwd())

    def _resolve_path(self, file_path: str) -> str:
        """
        Resolves a file path relative to the agent's base directory (CWD).
        Ensures the path is absolute for security checks.
        """
        # If the path is relative, os.path.abspath will resolve it against CWD.
        # Since the AgentCore sets CWD to the project root, this resolves correctly.
        return os.path.abspath(file_path)

    def execute_action(self, action: Action) -> str:
        """Dispatches the action based on its type and returns a status message."""
        
        # --- Handle READ_FILE ---
        if action.action == "READ_FILE":
            file_path_raw = action.parameters.get("file_path", "")
            resolved_path = self._resolve_path(file_path_raw)
            
            if not self.resources.is_file_path_safe(resolved_path):
                return f"Error: File path '{file_path_raw}' is unsafe or outside the allowed scope."
            
            try:
                content = read_text_file(resolved_path)
                self.memory.update_read_files(file_path_raw, content)
                return f"File content:\n--- {file_path_raw} ---\n{content}\n---"
            except FileNotFoundError:
                return f"Error: File not found at path: {file_path_raw}"
            except Exception as e:
                return f"Error reading file {file_path_raw}: {e}"

        # --- Handle WRITE_FILE ---
        elif action.action == "WRITE_FILE":
            file_path_raw = action.parameters.get("file_path", "")
            content = action.parameters.get("content", "")
            resolved_path = self._resolve_path(file_path_raw)
            
            if not self.resources.is_file_path_safe(resolved_path):
                return f"Error: File path '{file_path_raw}' is unsafe or outside the allowed scope."
            
            try:
                write_text_file(resolved_path, content)
                return f"Success: Wrote {len(content)} characters to file: {file_path_raw}"
            except Exception as e:
                return f"Error writing file {file_path_raw}: {e}"
        
        # --- Handle DELETE_FILE ---
        elif action.action == "DELETE_FILE":
            file_path_raw = action.parameters.get("file_path", "")
            resolved_path = self._resolve_path(file_path_raw)
            
            if not self.resources.is_file_path_safe(resolved_path):
                return f"Error: File path '{file_path_raw}' is unsafe or outside the allowed scope."
            
            try:
                delete_file(resolved_path)
                return f"Success: Deleted file: {file_path_raw}"
            except Exception as e:
                return f"Error deleting file {file_path_raw}: {e}"

        # --- Handle REFINE_PLAN ---
        elif action.action == "REFINE_PLAN":
            new_plan = action.parameters.get("development_plan", "")
            if new_plan:
                self.memory.update_development_plan(new_plan)
                return f"Development plan updated successfully."
            return "Warning: REFINE_PLAN received with no plan content."
            
        # --- Handle UNKNOWN ACTION ---
        else:
            return f"Error: Unknown action '{action.action}' executed."