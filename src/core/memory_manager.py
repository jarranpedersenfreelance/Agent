import os
from typing import List, Dict, Any, Optional

from . import agent_constants as constants
from .utilities import json_safe_load, json_safe_dump

class MemoryManager:
    """Manages the agent's long-term memory, including known files and plans."""

    DEFAULT_MEMORY_SCHEMA: Dict[str, Any] = {
        "known_files": [],
        "development_plan": "Determine best next step of growth based on current goals, codebase, and resources. Self-Update to achieve this growth, and then iterate.",
        "read_files": {}, # Optional: Store file contents read
    }

    def __init__(self, agent_root: str = constants.FILE_PATHS.ROOT):
        self.agent_root = agent_root
        
        self.mem_path = os.path.join(self.agent_root, constants.FILE_PATHS.MEMORY_STREAM_FILE)
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        """Loads the memory stream from its JSON file, applying a default schema."""
        data = json_safe_load(self.mem_path)
        
        # Merge loaded data over the default schema (Issue 5)
        memory_state = self.DEFAULT_MEMORY_SCHEMA.copy()
        memory_state.update(data)
            
        return memory_state

    def _save_memory(self):
        """Saves the current memory state to the JSON file."""
        json_safe_dump(self.mem_path, self.memory)

    def update_known_files(self, new_files: List[str], deleted_files: List[str]):
        """
        Updates the list of known files in memory.
        """
        known_files = set(self.memory.get("known_files", []))
        
        for f in new_files:
            known_files.add(f)
            
        for f in deleted_files:
            known_files.discard(f)

        self.memory["known_files"] = sorted(list(known_files))
        self._save_memory()

    def get_known_files(self) -> List[str]:
        """Returns the list of known files."""
        return self.memory.get("known_files", [])

    def update_plan(self, plan: str):
        """Updates the development plan in memory."""
        self.memory["development_plan"] = plan
        self._save_memory()