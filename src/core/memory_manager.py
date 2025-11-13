# src/core/memory_manager.py
import os
from typing import Dict, List # FIX: Added typing imports
from .utilities import json_load, json_dump
from .models import MemoryStream
from .constants import FILE_PATHS, AGENT

class MemoryManager:
    def __init__(self, constants):
        self.constants = constants
        self.memory_path = FILE_PATHS.MEMORY_STREAM_FILE
        self.stream = self._load_stream()

    def _load_stream(self) -> MemoryStream:
        """Loads the memory stream from a file, initializing if the file is missing or corrupt."""
        if os.path.exists(self.memory_path):
            try:
                data = json_load(self.memory_path)
                return MemoryStream.parse_obj(data)
            except (FileNotFoundError, ValueError, AttributeError, KeyError) as e:
                print(f"Warning: Could not load memory stream file ({e}). Initializing default memory.")
                return MemoryStream()
        else:
            return MemoryStream()

    def _save_stream(self):
        """Saves the current memory stream to the JSON file."""
        data = self.stream.dict()
        json_dump(data, self.memory_path)
        
    def add_context(self, role: str, message: str):
        """
        Adds a new message to the context history and truncates if necessary.
        (Issue 7)
        """
        entry = {"role": role, "message": message}
        self.stream.context_history.append(entry)
        
        # Truncate history based on configured limit (simple length-based truncation)
        max_limit = AGENT.CONTEXT_TRUNCATION_LIMIT
        if len(self.stream.context_history) > max_limit:
            # Keep the most recent messages
            self.stream.context_history = self.stream.context_history[-max_limit:]
            
        self._save_stream()
        
    def get_context(self) -> List[Dict[str, str]]:
        """Returns the current context history for use in the LLM call."""
        return self.stream.context_history
    
    # Placeholder for other memory methods (e.g., adding read files, known files)