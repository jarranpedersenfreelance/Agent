from typing import Any, Dict, List, Union
from core.definitions.models import Mem, Count, Action, Action_Type
from core.utilities import json_typed_load, json_dump, current_timestamp

class Memory:
    """Manages the agent's memory"""
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.memory_file = self.constants['FILE_PATHS']['MEMORY_FILE']
        self.memory = json_typed_load(Mem, self.memory_file)
        if (not self.memory.action_queue):
            self.reset_actions()

    def memorize(self):
        """Saves memory to disk."""
        # TODO: add file size checks that trigger compression functions
        # TODO: add validation to ensure memory isn't corrupted
        self.memory.last_memorized = current_timestamp()
        json_dump(self.memory, self.memory_file)

    def get_count(self, counter: Count) -> int:
        return self.memory.counters[counter]
    
    def inc_count(self, counter: Count) -> int:
        self.memory.counters[counter] += 1
        return self.memory.counters[counter]
    
    def set_count(self, counter: Count, val: int):
        self.memory.counters[counter] = val

    def reset_actions(self):
        starting_task = self.constants['AGENT']['STARTING_TASK']
        initial_action = Action(
            type=Action_Type.REASON, 
            arguments={"task": starting_task}
        )
        self.memory.action_queue = [initial_action]

    def pop_action(self) -> Union[Action, None]:
        """Removes and returns the next action from the front of the queue."""
        if not self.memory.action_queue:
            return None
        
        return self.memory.action_queue.pop(0)

    def add_action(self, action: Action):
        """Adds a single action to the end of the queue."""
        self.memory.action_queue.append(action)

    def add_actions(self, actions: List[Action]):
        """Adds a list of actions to the end of the queue."""
        if actions:
            self.memory.action_queue.extend(actions)
