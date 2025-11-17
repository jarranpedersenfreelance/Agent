from typing import Any, Dict, List, Union
from core.logger import Logger
from core.definitions.models import Mem, Count, Action, ReasonAction
from core.utilities import json_typed_load, json_dump, current_timestamp, scan_workspace

class Memory:
    """Manages the agent's memory"""
    
    def __init__(self, constants: Dict[str, Any], logger: Logger, mock: bool = False):
        self.constants = constants
        self.logger = logger
        self.mock = mock
        if not mock:
            self.memory_file = self.constants['FILE_PATHS']['MEMORY_FILE']
            self.memory = json_typed_load(Mem, self.memory_file)
        else:
            self.memory_file = self.constants['FILE_PATHS']['TEST_MEMORY_FILE']
            self.memory = json_typed_load(Mem, self.constants['FILE_PATHS']['SRC_MEMORY_FILE'])

        self.memory.deployed_at = current_timestamp()
        
        # Initialize action queue if empty
        if (not self.memory.action_queue):
            self.reset_actions(self.constants['AGENT']['STARTING_TASK'], "initial action")
            
        # Initialize file_contents with file structure if empty
        if (not self.memory.file_contents):
            self.logger.log_info("Initializing file structure in memory")
            file_paths = scan_workspace(root_dir=".")
            self.memory.file_contents = {path: "" for path in file_paths}
            self.logger.log_info(f"Tracked {len(file_paths)} files")

        # Load recent logs
        self.load_logs()
        self.memorize()

    def memorize(self):
        """Saves memory to disk."""
        # mock memory used for tests isn't saved to disk
        if self.mock:
            return
        # TODO: add file size checks that trigger compression functions
        # TODO: add validation to ensure memory isn't corrupted
        self.memory.last_memorized = current_timestamp()
        json_dump(self.memory, self.memory_file)

    def deployed_at(self) -> str:
        return self.memory.deployed_at

    def is_test(self) -> bool:
        return self.memory.mock

    def last_memorized(self) -> str:
        return self.memory.last_memorized
    
    def load_logs(self):
        self.memory.logs = self.logger.recent_logs()
    
    def get_filepaths(self) -> List[str]:
        return [k for k in self.memory.file_contents]
    
    def get_file_contents(self, file_path: str):
        return self.memory.file_contents[file_path]
    
    def fill_file_contents(self, file_path: str, contents: str):
        self.memory.file_contents[file_path] = contents

    def remove_file(self, file_path: str):
        del self.memory.file_contents[file_path]
    
    def get_todo_list(self) -> List[str]:
        return self.memory.todo.copy()

    def remove_todo(self):
        self.memory.todo.pop(0)

    def add_todo(self, item: str):
        self.memory.todo.append(item)

    def add_immediate_todo(self, item: str):
        self.memory.todo.insert(0, item)

    def get_count(self, counter: Count) -> int:
        return self.memory.counters[counter]
    
    def inc_count(self, counter: Count) -> int:
        self.memory.counters[counter] += 1
        return self.memory.counters[counter]
    
    def set_count(self, counter: Count, val: int):
        self.memory.counters[counter] = val

    def list_counts(self) -> Dict[Count, int]:
        return self.memory.counters.copy()
    
    def reset_actions(self, start_task: str, explanation: str):
        action = ReasonAction()
        action.task = start_task
        action.explanation = explanation
        self.memory.action_queue = [action]

    def empty_actions(self):
        self.memory.action_queue = []

    def pop_action(self) -> Union[Action, None]:
        """Removes and returns the next action from the front of the queue."""
        if not self.memory.action_queue:
            return None
        return self.memory.action_queue.pop(0)
    
    def pop_last_action(self) -> Union[Action, None]:
        """Removes and returns the last action from the end of the queue."""
        if not self.memory.action_queue:
            return None
        return self.memory.action_queue.pop()

    def add_action(self, action: Action):
        """Adds a single action to the end of the queue."""
        self.memory.action_queue.append(action)

    def prepend_action(self, action: Action):
        """Adds a single action to the start of the queue."""
        self.memory.action_queue.insert(0,action)

    def add_actions(self, actions: List[Action]):
        """Adds a list of actions to the end of the queue."""
        if actions:
            self.memory.action_queue.extend(actions)

    def list_actions(self) -> List[Action]:
        """Gets a copy of the action queue."""
        return self.memory.action_queue.copy()

    def set_thought(self, label: str, thought: str):
        """Adds or overwrites an indexed thought."""
        self.memory.thoughts[label] = thought

    def list_thoughts(self) -> List[str]:
        """Lists all thought labels."""
        return list(self.memory.thoughts.keys())
    
    def get_thought(self, label: str) -> str:
        """Gets the content of a single thought."""
        return self.memory.thoughts[label]
    
    def remove_thought(self, label: str):
        """Removes a single thought."""
        del self.memory.thoughts[label]

    def forget(self):
        """Removes all thoughts."""
        self.memory.thoughts = {}