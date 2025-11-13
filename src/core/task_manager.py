# src/core/task_manager.py
import os
from typing import Dict, Any, List
from .utilities import json_load, json_dump

class TaskManager:
    """
    Manages the queue of actions/tasks for the agent.
    """

    def __init__(self, constants: Dict[str, Any] = None):
        
        # FIX: Updated to access structured constants (Issue 10)
        file_paths = constants.get('FILE_PATHS', {})
        agent_config = constants.get('AGENT', {})

        if file_paths and file_paths.get('ACTION_QUEUE_FILE'):
            self.queue_path = file_paths['ACTION_QUEUE_FILE']
        else:
            self.queue_path = "workspace/data/action_queue.json"
        
        self.action_queue: List[Dict[str, Any]] = self._load_queue()
        
        # FIX: Issue 7 - Uses STARTING_TASK constant and manages current_task state
        self.current_task = agent_config.get('STARTING_TASK', "Begin self-improvement cycle.")


    # --- Task Queue Persistence ---

    def _load_queue(self) -> List[Dict[str, Any]]:
        """
        FIX: Issue 1 - Loads the action queue from a JSON file.
        """
        if not os.path.exists(self.queue_path):
            return []
        try:
            return json_load(self.queue_path)
        except Exception as e:
            print(f"Warning: Failed to load action queue from {self.queue_path}: {e}")
            return []

    def _save_queue(self):
        """
        FIX: Issue 1 - Saves the current action queue state to the JSON file.
        """
        try:
            json_dump(self.action_queue, self.queue_path)
        except Exception as e:
            print(f"ERROR: Failed to save action queue to {self.queue_path}: {e}")

    # --- Task Queue Management ---

    def enqueue_action(self, action_dict: Dict[str, Any]):
        """
        FIX: Issue 1 - Adds an action dictionary to the end of the queue.
        Action dict format should be ready for execution (e.g., {'action': 'READ_FILE', 'parameters': {...}})
        """
        self.action_queue.append(action_dict)
        self._save_queue()

    def dequeue_action(self) -> Union[Dict[str, Any], None]:
        """
        FIX: Issue 1 - Removes and returns the next action dictionary from the front of the queue.
        """
        if not self.action_queue:
            return None
        action = self.action_queue.pop(0)
        self._save_queue()
        return action

    def has_pending_actions(self) -> bool:
        """Checks if there are any actions currently in the queue."""
        return len(self.action_queue) > 0

    def get_current_task(self) -> str:
        """Returns the current high-level task the agent is working on."""
        return self.current_task

    def update_current_task(self, new_task: str):
        """Updates the agent's current task based on its latest reasoning."""
        self.current_task = new_task
        # Note: Task persistence is handled through the MemoryManager/ActionLog, 
        # not the TaskManager's save state.

    # TODO: Implement Issue 8 - parse_action_from_response(raw_text)