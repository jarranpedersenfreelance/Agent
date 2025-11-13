# src/core/memory_manager.py
import os
import json # FIX: Added missing import for json.JSONDecodeError
from typing import Any, Dict
from .utilities import json_load, json_dump

# --- Memory Manager ---

class MemoryManager:
    """Manages the agent's persistent memory stream, including read file contents."""
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.memory_file = os.path.join(
            "workspace", self.constants['FILE_PATHS']['MEMORY_STREAM_FILE']
        )
        self.truncation_limit = self.constants['AGENT']['CONTEXT_TRUNCATION_LIMIT']
        self._load_state()

    def _load_state(self):
        """Loads the memory stream from disk."""
        try:
            self.memory_stream = json_load(self.memory_file)
        except (FileNotFoundError, json.JSONDecodeError): # Uses json.JSONDecodeError
            self.memory_stream = self._get_default_state()
        
        self._save_state()

    def _save_state(self):
        """Saves the current memory stream to disk."""
        json_dump(self.memory_stream, self.memory_file)

    def _get_default_state(self) -> Dict[str, Any]:
        """Returns the default memory state."""
        return {
            'development_plan': "Initial plan: Analyze codebase.",
            'read_files': {},
            'known_files': [] # List of files the agent is aware of
        }

    def update_development_plan(self, new_plan: str):
        """Updates the agent's current long-term development plan."""
        self.memory_stream['development_plan'] = new_plan
        self._save_state()

    def get_development_plan(self) -> str:
        """Returns the current development plan."""
        return self.memory_stream['development_plan']

    def update_read_files(self, file_path: str, content: str):
        """
        Stores the content of a recently read file, truncating it if necessary.
        """
        if len(content) > self.truncation_limit:
            # Truncate content and append ellipsis
            truncated_content = content[:self.truncation_limit] + "..."
            self.memory_stream['read_files'][file_path] = truncated_content
        else:
            self.memory_stream['read_files'][file_path] = content
            
        self._save_state()

    def get_read_files_context(self) -> Dict[str, str]:
        """Returns the dictionary of all currently tracked read file contents."""
        return self.memory_stream['read_files']