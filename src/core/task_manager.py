# src/core/task_manager.py
from .utilities import read_text_file, write_text_file
from .constants import FILE_PATHS

class TaskManager:
    def __init__(self, constants):
        self.constants = constants
        
    def get_goal(self) -> str:
        """Reads the immutable top-level goal."""
        try:
            return read_text_file(FILE_PATHS.GOAL_FILE)
        except FileNotFoundError:
            return "ERROR: Top-level goal file not found. Default goal: self-evolve."
            
    def get_reasoning_principles(self) -> str:
        """Reads the immutable reasoning principles."""
        try:
            return read_text_file(FILE_PATHS.REASONING_PRINCIPLES_FILE)
        except FileNotFoundError:
            return "ERROR: Reasoning principles file not found. Default principle: follow the scientific method."

    def get_immediate_task(self) -> str:
        """Reads the mutable immediate task."""
        try:
            return read_text_file(FILE_PATHS.IMMEDIATE_TASK_FILE)
        except FileNotFoundError:
            return "ERROR: Immediate task file not found. Current task: Resolve setup and dependency issues."
            
    def write_immediate_task(self, new_task_content: str) -> str:
        """
        Allows the agent to self-update its immediate task. 
        Used by the 'agent_set_goals' action (Issue 9 Modification).
        """
        try:
            write_text_file(FILE_PATHS.IMMEDIATE_TASK_FILE, new_task_content)
            return f"Success: Immediate task file '{FILE_PATHS.IMMEDIATE_TASK_FILE}' successfully updated."
        except Exception as e:
            return f"Error: Failed to write to immediate task file: {e}"