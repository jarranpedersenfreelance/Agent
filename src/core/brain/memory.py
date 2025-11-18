from typing import Any, Dict, List, Union
from core.logger import Logger
from core.definitions.models import Mem, Count, Action, ReasonAction
from core.utilities import json_typed_load, json_dump, current_timestamp, scan_files

class Memory:
    """Manages the agent's memory"""
    
    def __init__(self, constants: Dict[str, Any], logger: Logger, is_test: bool):
        self._constants = constants
        self._logger = logger
        self._memory_file = self._constants['FILE_PATHS']['MEMORY_FILE']
        self._mem = json_typed_load(Mem, self._memory_file)
        self._mem.is_test = is_test
        self._mem.deployed_at = current_timestamp()
        
        # Initialize action queue if empty
        if (not self._mem.action_queue):
            self.reset_actions(self._constants['AGENT']['STARTING_TASK'], "initial action")
            
        # Initialize file_contents with file structure if empty
        if (not self._mem.file_contents):
            self._logger.log_info("Initializing file structure in memory")
            file_paths = scan_files()
            self._mem.file_contents = {path: "" for path in file_paths}
            self._logger.log_info(f"Tracked {len(file_paths)} files")

        # Load recent logs
        self.load_logs()
        self.memorize()

    def memorize(self):
        """Saves memory to disk."""
        # TODO: add file size checks that trigger compression functions
        # TODO: add validation to ensure memory isn't corrupted
        self._mem.last_memorized = current_timestamp()
        json_dump(self._mem, self._memory_file)

    def deployed_at(self) -> str:
        return self._mem.deployed_at

    def is_test(self) -> bool:
        return self._mem.is_test

    def last_memorized(self) -> str:
        return self._mem.last_memorized
    
    def load_logs(self):
        self._mem.logs = self._logger.recent_logs()
    
    def get_filepaths(self) -> List[str]:
        return [k for k in self._mem.file_contents]
    
    def get_file_contents(self, file_path: str):
        return self._mem.file_contents[file_path]
    
    def fill_file_contents(self, file_path: str, contents: str):
        self._mem.file_contents[file_path] = contents

    def remove_file(self, file_path: str):
        del self._mem.file_contents[file_path]
    
    def get_todo_list(self) -> List[str]:
        return self._mem.todo.copy()

    def remove_todo(self):
        self._mem.todo.pop(0)

    def add_todo(self, item: str):
        self._mem.todo.append(item)

    def add_immediate_todo(self, item: str):
        self._mem.todo.insert(0, item)

    def get_count(self, counter: Count) -> int:
        return self._mem.counters[counter]
    
    def inc_count(self, counter: Count) -> int:
        self._mem.counters[counter] += 1
        return self._mem.counters[counter]
    
    def set_count(self, counter: Count, val: int):
        self._mem.counters[counter] = val

    def list_counts(self) -> Dict[Count, int]:
        return self._mem.counters.copy()
    
    def reset_actions(self, start_task: str, explanation: str):
        action = ReasonAction()
        action.task = start_task
        action.explanation = explanation
        self._mem.action_queue = [action]

    def empty_actions(self):
        self._mem.action_queue = []

    def pop_action(self) -> Action:
        """Removes and returns the next action from the front of the queue."""
        if not self._mem.action_queue:
            raise LookupError("Tried to pop empty action queue")
        return self._mem.action_queue.pop(0)
    
    def pop_last_action(self) -> Action:
        """Removes and returns the last action from the end of the queue."""
        if not self._mem.action_queue:
            raise LookupError("Tried to pop empty action queue")
        return self._mem.action_queue.pop()

    def add_action(self, action: Action):
        """Adds a single action to the end of the queue."""
        self._mem.action_queue.append(action)

    def prepend_action(self, action: Action):
        """Adds a single action to the start of the queue."""
        self._mem.action_queue.insert(0,action)

    def add_actions(self, actions: List[Action]):
        """Adds a list of actions to the end of the queue."""
        if actions:
            self._mem.action_queue.extend(actions)

    def list_actions(self) -> List[Action]:
        """Gets a copy of the action queue."""
        return self._mem.action_queue.copy()

    def set_thought(self, label: str, thought: str):
        """Adds or overwrites an indexed thought."""
        self._mem.thoughts[label] = thought

    def list_thoughts(self) -> List[str]:
        """Lists all thought labels."""
        return list(self._mem.thoughts.keys())
    
    def get_thought(self, label: str) -> str:
        """Gets the content of a single thought."""
        return self._mem.thoughts[label]
    
    def remove_thought(self, label: str):
        """Removes a single thought."""
        del self._mem.thoughts[label]

    def forget(self):
        """Removes all thoughts."""
        self._mem.thoughts = {}