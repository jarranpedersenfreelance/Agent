# src/core/task_manager.py

import json
from typing import Dict, Any, List, Tuple
from core.utilities import read_text_file

class TaskManager:
    """Manages the immediate_task.txt (human task) and action_queue.json (machine queue)."""

    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.task_file = constants['PATHS']['IMMEDIATE_TASK_FILE']
        self.queue_file = constants['PATHS']['ACTION_QUEUE_FILE'] 

    def load_queue(self) -> List[str]:
        """Loads the action queue from JSON."""
        try:
            with open(self.queue_file, 'r') as f:
                queue = json.load(f)
                return queue if isinstance(queue, list) else []
        except FileNotFoundError:
            return []
        except Exception as e:
            # CRITICAL FIX: Log the specific error type to debug the infinite decomposition loop
            print(f"[ERROR] Failed to load action queue: {type(e).__name__}: {e}")
            return []
            
    def save_queue(self, queue: List[str]) -> str:
        """Saves the action queue to JSON."""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(queue, f, indent=2)
            return "Success: Action queue saved."
        except Exception as e:
            return f"Error: Failed to save action queue: {e}"

    def get_next_action(self) -> Tuple[str, str]:
        """Reads the action queue and returns the next action or signals for decomposition."""
        queue = self.load_queue()
        
        if queue:
            return queue[0], "QUEUE_ACTION"
        else:
            human_task = read_text_file(self.task_file)
            if human_task.startswith("ERROR"):
                return "SLUMBER: 5", "ERROR"
            
            return human_task, "DECOMPOSITION_NEEDED" 

    def pop_next_action(self, memory_stream: str) -> Tuple[str, str]:
        """Removes the first action from the queue after execution."""
        queue = self.load_queue()
        
        if queue:
            popped_action = queue.pop(0)
            self.save_queue(queue)
            new_memory_stream = f"{memory_stream}\n[QUEUE POP] Executed action '{popped_action[:50]}...' removed from queue."
            return f"Success: Action '{popped_action[:50]}...' popped from queue.", new_memory_stream
        
        return "Warning: Attempted to pop from empty queue.", memory_stream

    def handle_next_task(self, memory_stream: str, new_task_directive: str) -> Tuple[str, str]:
        """
        Clears the action queue, updates immediate_task.txt with the new_task_directive, 
        and signals the start of a new task cycle.
        """
        # 1. Update immediate_task.txt with the new task provided by the LLM
        try:
            with open(self.task_file, 'w') as f:
                f.write(new_task_directive)
            task_update_result = f"Success: Updated immediate_task.txt with new directive: '{new_task_directive[:100]}...'"
        except Exception as e:
            task_update_result = f"Error: Failed to write new task to {self.task_file}: {e}"

        # 2. Clear the action queue (crucial step to force DECOMPOSITION_NEEDED next cycle)
        queue_result = self.save_queue([])
        
        # 3. Update memory stream
        new_memory_stream = (
            f"{memory_stream}\n"
            f"[TASK COMPLETED & NEXT TASK SET]\n"
            f"  - Old Task completed.\n"
            f"  - New High-Level Task Directive: {new_task_directive}\n"
            f"  - {queue_result}\n"
            f"  - {task_update_result}"
        )
        
        return f"Success: Current task cycle finished. New task set. Queue cleared. Next cycle will trigger decomposition.", new_memory_stream