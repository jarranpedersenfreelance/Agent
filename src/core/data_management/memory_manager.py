from typing import Any, Dict, List
from core.definitions.models import Memory, Counter
from core.utilities import json_load, json_dump

class MemoryManager:
    """Manages the agent's persistent memory stream, including read file contents and a transient event log."""
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.memory_file = self.constants['FILE_PATHS']['MEMORY_FILE']
        self.memory: Memory
        self._load_state()

    def _load_state(self):
        """Loads the memory stream from disk."""
        self.memory = json_load(self.memory_file)

    def memorize(self):
        """Saves the current memory stream to disk."""
        # TODO: add file size checks that trigger compression functions
        # TODO: add validation to ensure memory isn't corrupted
        json_dump(self.memory, self.memory_file)

    def get_reasoning_count(self) -> int:
        return self.memory.counters[Counter.REASONING]
    
    def inc_reasoning_count(self):
        self.memory.counters[Counter.REASONING] += 1
        self.memorize()
    
    def reset_reasoning_count(self):
        self.memory.counters[Counter.REASONING] = 0
        self.memorize()
