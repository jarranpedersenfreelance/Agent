# src/core/memory_manager.py
import os
import json
from typing import Dict, Any, Union
from .utilities import json_load, json_dump

class MemoryManager:
    """
    Manages the persistent memory stream for the Agent, which includes known files, 
    the development plan, and recently read file contents.
    """

    def __init__(self, constants: Dict[str, Any] = None):
        
        # FIX: Updated to access structured constants (Issue 10)
        file_paths = constants.get('FILE_PATHS', {})
        agent_config = constants.get('AGENT', {})

        if file_paths and file_paths.get('MEMORY_STREAM_FILE'):
            self.stream_path = file_paths['MEMORY_STREAM_FILE']
        else:
            self.stream_path = "workspace/data/memory_stream.json"
            
        self.context_limit = agent_config.get('CONTEXT_TRUNCATION_LIMIT', 500)
            
        self.memory_stream = self._load_stream()

    def _load_stream(self) -> Dict[str, Any]:
        """Loads the memory stream from a JSON file, handling errors."""
        try:
            return json_load(self.stream_path)
        except FileNotFoundError:
            # Return default initial state
            return {
                "read_files": {},
                "development_plan": "Determine best next step of growth based on current goals, codebase, and resources. Self-Update to achieve this growth, and then iterate.",
                "known_files": []
            }
        except Exception as e:
            print(f"Warning: Failed to load memory stream from {self.stream_path}: {e}")
            return {} # Return empty dict on severe error

    def _save_stream(self):
        """Saves the current memory stream state to the JSON file."""
        try:
            json_dump(self.memory_stream, self.stream_path)
        except Exception as e:
            print(f"ERROR: Failed to save memory stream to {self.stream_path}: {e}")

    def update_read_files(self, file_path: str, content: str):
        """
        FIX: Issue 5 - Updates the read_files dictionary, truncating content if necessary.
        """
        # Apply truncation limit to the content
        if len(content) > self.context_limit:
            content = content[:self.context_limit] + "..." # Truncate and indicate truncation

        self.memory_stream['read_files'][file_path] = content
        self._save_stream()

    def get_read_files_context(self) -> Dict[str, str]:
        """Returns the dictionary of recently read files and their (potentially truncated) content."""
        return self.memory_stream.get('read_files', {})

    def get_development_plan(self) -> str:
        """Returns the current long-term development plan."""
        return self.memory_stream.get('development_plan', "")

    def update_development_plan(self, new_plan: str):
        """Sets a new long-term development plan."""
        self.memory_stream['development_plan'] = new_plan
        self._save_stream()