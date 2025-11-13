# src/core/action_handler.py
from typing import Dict, Any # FIX: Added typing imports
from .resource_manager import ResourceManager
from .memory_manager import MemoryManager
from .task_manager import TaskManager
from .utilities import read_text_file, write_text_file, sanitize_filename
from .constants import FILE_PATHS

class ActionHandler:
    def __init__(self, managers: Dict[str, Any]):
        self.resource_manager: ResourceManager = managers['resource_manager']
        self.memory_manager: MemoryManager = managers['memory_manager']
        self.task_manager: TaskManager = managers['task_manager']
        
    def execute_action(self, action: str, parameters: Dict[str, str]) -> str:
        """Routes and executes the requested action."""
        
        if action == 'read_file':
            return self._read_file(parameters)
        elif action == 'write_file':
            return self._write_file(parameters)
        elif action == 'agent_set_goals':
            return self._agent_set_goals(parameters)
        elif action == 'exit_and_finish':
            return self._exit_and_finish(parameters)
        
        return f"Error: Unknown action '{action}'. Action not executed. Ensure the action name is correct and supported."

    def _read_file(self, parameters: Dict[str, str]) -> str:
        """Reads the content of a file. (Fixes Issue 4 error format)"""
        path = parameters.get('path', '').strip()
        
        if not path:
            return "Error: The 'read_file' action requires a 'path' parameter."
        
        sanitized_path = sanitize_filename(path)
        
        try:
            content = read_text_file(sanitized_path)
            
            # Return content in the expected format (Issue 4 fix)
            return (
                f"File content:\n"
                f"--- START {sanitized_path} ---\n"
                f"{content}\n"
                f"--- END {sanitized_path} ---"
            )
        except FileNotFoundError:
            # Return standardized error message
            return f"Error: File '{sanitized_path}' not found."
        except Exception as e:
            return f"Error: Failed to read file '{sanitized_path}': {e}"

    def _write_file(self, parameters: Dict[str, str]) -> str:
        """Writes content to a file."""
        path = parameters.get('path', '').strip()
        content = parameters.get('content', '')
        
        if not path:
            return "Error: The 'write_file' action requires both 'path' and 'content' parameters."
        
        sanitized_path = sanitize_filename(path)
        
        try:
            write_text_file(sanitized_path, content)
            return f"Success: File '{sanitized_path}' written successfully."
        except Exception as e:
            return f"Error: Failed to write to file '{sanitized_path}': {e}"
            
    def _agent_set_goals(self, parameters: Dict[str, str]) -> str:
        """
        Allows the agent to update its immediate task based on its reasoning.
        (Issue 9 Modification)
        """
        new_task = parameters.get('new_task', '').strip()
        
        if not new_task:
            return "Error: The 'agent_set_goals' action requires a 'new_task' parameter."
        
        return self.task_manager.write_immediate_task(new_task)

    def _exit_and_finish(self, parameters: Dict[str, str]) -> str:
        """Tells the agent to finish its current task and exit the loop."""
        reason = parameters.get('reason', 'Goal achieved or unachievable.')
        return f"FINISH SIGNAL: The agent is exiting the loop. Reason: {reason}"