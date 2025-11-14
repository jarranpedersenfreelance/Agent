from typing import Any, Dict, List, Union
from core.data_management.memory_manager import MemoryManager
from core.definitions.models import Action, Action_Type
from core.utilities import json_load, json_dump

class TaskManager:
    """Manages the action queue and task state for the agent."""
    
    def __init__(self, constants: Dict[str, Any], memory_manager: MemoryManager):
        self.constants = constants
        self.memory_manager = memory_manager
        self.queue = memory_manager.memory['action_queue']
        if (not self.queue):
            self.queue = self._get_default_queue()
            self.memory_manager.memorize()
        

    def _get_default_queue(self) -> List[Action]:
        """Returns the default action queue: a single REASON action."""
        starting_task = self.constants['AGENT']['STARTING_TASK']
        initial_action = Action(
            type=Action_Type.REASON, 
            arguments={"task": starting_task}
        )
        return [initial_action]

    def dequeue_action(self) -> Union[Action, None]:
        """Removes and returns the next action from the front of the queue."""
        if not self.queue:
            return None
        
        action = self.queue.pop(0)
        self.memory_manager.memorize()
        return action

    def add_action(self, action: Action):
        """Adds a single action to the end of the queue."""
        self.queue.append(action)
        self.memory_manager.memorize()

    def add_actions(self, actions: List[Action]):
        """Adds a list of actions to the end of the queue."""
        if actions:
            self.queue.extend(actions)
            self.memory_manager.memorize()

    def get_queue_contents(self) -> List[Dict[str, Any]]:
        """Returns a list of the queue contents for inspection."""
        return [item.model_dump() for item in self.queue]