import os
from typing import List, Dict, Any, Optional

from . import agent_constants as constants
from .utilities import json_safe_load, json_safe_dump, load_file_content, write_text_file 

class TaskManager:
    """Manages the agent's immediate task and action queue."""

    def __init__(self, agent_root: str = constants.FILE_PATHS.ROOT):
        self.agent_root = agent_root
        
        self.immediate_task_path = os.path.join(self.agent_root, constants.FILE_PATHS.IMMEDIATE_TASK_FILE)
        self.action_queue_path = os.path.join(self.agent_root, constants.FILE_PATHS.ACTION_QUEUE_FILE)
        
        self.action_queue: List[Dict[str, Any]] = self._load_action_queue()

    def _load_action_queue(self) -> List[Dict[str, Any]]:
        """Loads the action queue from its JSON file."""
        data = json_safe_load(self.action_queue_path)
        return data if isinstance(data, list) else []

    def _save_action_queue(self):
        """Saves the action queue to its JSON file."""
        json_safe_dump(self.action_queue_path, self.action_queue)

    def pop_next_action(self) -> Optional[str]:
        """
        Pops the next action from the queue and returns it as a formatted string.
        Returns None if the queue is empty.
        """
        if self.action_queue:
            next_action = self.action_queue.pop(0)
            self._save_action_queue()
            
            # Format the action as ACTION_TYPE: arg1 arg2 ...
            action_type = next_action.get("type", "SLUMBER")
            # Args are already a list of strings
            args = next_action.get("args", [])
            
            # If args is only one item, it's often the content of a WRITE_FILE, 
            # so we join with space and let the ActionHandler parse it.
            arg_string = ' '.join(args)
            
            return f"{action_type}: {arg_string}"
        else:
            return None 

    def clear_immediate_task(self) -> bool:
        """Clears the contents of the immediate task file."""
        return write_text_file(self.immediate_task_path, "")

    def set_immediate_task(self, content: str) -> bool:
        """Sets the content of the immediate task file."""
        return write_text_file(self.immediate_task_path, content)

    def get_immediate_task(self) -> str:
        """Gets the content of the immediate task file."""
        return load_file_content(self.immediate_task_path)