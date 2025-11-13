# src/core/task_manager.py
import os
import json # FIX: Added missing import for json.JSONDecodeError
from typing import Any, Dict, Union
from .utilities import json_load, json_dump

# --- Task Manager ---

class TaskManager:
    """Manages the current task and the queue of actions for the agent."""
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.queue_file = os.path.join(
            "workspace", self.constants['FILE_PATHS']['ACTION_QUEUE_FILE']
        )
        self.current_task = self.constants['AGENT']['STARTING_TASK']
        self._load_state()

    def _load_state(self):
        """Loads the action queue from disk."""
        try:
            # Load action queue
            self.action_queue = json_load(self.queue_file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.action_queue = []
        
        # NOTE: current_task is set during init and is not persistent here
        self._save_state()

    def _save_state(self):
        """Saves the action queue to disk."""
        json_dump(self.action_queue, self.queue_file)

    def update_current_task(self, new_task: str):
        """Updates the agent's current task."""
        self.current_task = new_task
        # Note: current_task is not persisted, relying on memory manager/LLM context

    def get_current_task(self) -> str:
        """Returns the agent's current task."""
        return self.current_task

    def enqueue_action(self, action: Dict[str, Any]):
        """Adds an action dict to the end of the queue."""
        self.action_queue.append(action)
        self._save_state()

    def dequeue_action(self) -> Union[Dict[str, Any], None]:
        """Removes and returns the next action from the front of the queue (FIFO)."""
        if self.action_queue:
            action = self.action_queue.pop(0)
            self._save_state()
            return action
        return None

    def has_pending_actions(self) -> bool:
        """Returns True if the action queue is not empty."""
        return len(self.action_queue) > 0