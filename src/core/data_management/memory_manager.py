import os
from typing import Any, Dict, List
from core.utilities import json_load, json_dump

class MemoryManager:
    """Manages the agent's persistent memory stream, including read file contents and a transient event log."""
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.memory_file = os.path.join(
            "workspace", self.constants['FILE_PATHS']['MEMORY_STREAM_FILE']
        )
        self.action_history: List[str] = [] 
        self._load_state()

    def _load_state(self):
        """Loads the memory stream from disk."""
        self.memory_stream = json_load(self.memory_file)

    def _save_state(self):
        """Saves the current memory stream to disk."""
        json_dump(self.memory_stream, self.memory_file)

    # TODO add functions to read/write/delete certain fields in memory
    # TODO add functions to manage memory field sizes (summarization or deletion required at max size)