# src/core/task_manager.py
import os
import json
from typing import Any, Dict, List, Union
from .models import Action
from .utilities import json_load, json_dump

class TaskManager:
    """Manages the action queue and task state for the agent."""
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.queue_file = os.path.join(
            "workspace", self.constants['FILE_PATHS']['ACTION_QUEUE_FILE']
        )
        self._load_queue()

    def _load_queue(self):
        """Loads the action queue from disk, or initializes default."""
        try:
            raw_queue = json_load(self.queue_file)
            self.queue = [Action(**item) for item in raw_queue]
        except FileNotFoundError:
            self.queue = self._get_default_queue()
            self._save_queue()
        except json.JSONDecodeError:
            print(f"Warning: Action queue file {self.queue_file} is corrupted. Resetting to default.")
            self.queue = self._get_default_queue()
            self._save_queue()

    def _save_queue(self):
        """Saves the current action queue to disk."""
        json_dump([item.model_dump() for item in self.queue], self.queue_file)

    def _get_default_queue(self) -> List[Action]:
        """Returns the default action queue: a single REASON action."""
        starting_task = self.constants['AGENT']['STARTING_TASK']
        initial_action = Action(
            type="REASON", 
            payload={"task": starting_task}
        )
        # FIX: Ensure fresh deployments start with a REASON action
        return [initial_action]

    def dequeue_action(self) -> Union[Action, None]:
        """Removes and returns the next action from the front of the queue."""
        if not self.queue:
            return None
        
        action = self.queue.pop(0)
        self._save_queue()
        return action

    def add_action(self, action: Action):
        """Adds a single action to the end of the queue."""
        self.queue.append(action)
        self._save_queue()

    def add_actions(self, actions: List[Action]):
        """Adds a list of actions to the end of the queue."""
        # FIX: New helper method to add multiple actions efficiently
        if actions:
            self.queue.extend(actions)
            self._save_queue()

    def get_queue_status(self) -> List[Dict[str, Any]]:
        """Returns a list of the queue contents for inspection."""
        return [item.model_dump() for item in self.queue]