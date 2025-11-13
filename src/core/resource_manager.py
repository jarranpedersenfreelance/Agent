# src/core/resource_manager.py
import os
from datetime import date
from typing import Dict, Any
from .utilities import yaml_safe_load, yaml_safe_dump 
# Removed: from .constants import FILE_PATHS, AGENT (Issue 5)

class ResourceManager:
    """
    Manages resource limits (like daily reasoning steps) and agent state (like termination status).
    """

    def __init__(self, constants: Dict[str, Any] = None):
        
        # FIX: Updated to access structured constants (Issue 10)
        file_paths = constants.get('FILE_PATHS', {})
        agent_config = constants.get('AGENT', {})

        # Use a sensible default path for the state file
        if file_paths and file_paths.get('RESOURCES_STATE_FILE'):
            self.state_file_path = file_paths['RESOURCES_STATE_FILE']
        else:
            # Fallback for testing/initialization outside of the main loop
            self.state_file_path = "workspace/data/resource_state.yaml"
            
        self.max_reasoning_steps = agent_config.get('MAX_REASONING_STEPS', 100)
        
        self.resources = self._load_state()
        self.last_run_date = self.resources.get('last_run_date')
        self._check_daily_reset()
        
        # The base directory where file operations are allowed to occur
        self.workspace_dir = os.path.abspath('workspace') 


    # --- Initialization and Persistence ---

    def _load_state(self) -> Dict[str, Any]:
        """Loads the resource state from a YAML file, handling errors."""
        try:
            # Using the new safe load function
            return yaml_safe_load(self.state_file_path)
        except FileNotFoundError:
            # New run, return default empty state
            return {}
        except Exception as e:
            print(f"Warning: Failed to load resource state from {self.state_file_path}: {e}")
            return {}

    def _save_state(self):
        """Saves the current resource state to the YAML file."""
        try:
            # Using the new safe dump function
            yaml_safe_dump(self.resources, self.state_file_path)
        except Exception as e:
            print(f"ERROR: Failed to save resource state to {self.state_file_path}: {e}")

    def _check_daily_reset(self):
        """Checks if a new day has started and resets daily resources if necessary."""
        today = date.today() 
        
        # Ensure the date is saved as a date object (not a string)
        if isinstance(self.last_run_date, str):
             # Try to parse the string date
             try:
                 # Assuming the string format is YYYY-MM-DD
                 self.last_run_date = date.fromisoformat(self.last_run_date)
             except ValueError:
                 self.last_run_date = None # Invalid format, force reset

        if self.last_run_date is None or today > self.last_run_date:
            # New day, reset resources
            self.set_resource('daily_reasoning_count', self.max_reasoning_steps)
            self.set_resource('last_run_date', today)
            print(f"INFO: Daily resources reset for {today.isoformat()}. Reasoning steps: {self.max_reasoning_steps}")
        else:
            # Same day, update date tracking for consistency, but don't reset count
            self.set_resource('last_run_date', today)

    # --- Public Methods for Resource Management ---

    def get_resource(self, key):
        """Retrieves a resource value by key."""
        return self.resources.get(key)

    def set_resource(self, key, value):
        """Sets a resource value by key and saves the state."""
        self.resources[key] = value
        self._save_state()

    def clear_state(self):
        """Clears the entire resource state (for development resets)."""
        self.resources = {}
        self._save_state()
        print("INFO: Resource state has been cleared.")

    def is_file_path_safe(self, file_path: str) -> bool:
        """
        FIX: Issue 4 - Implements security check to ensure file access is confined to the workspace.
        Prevents directory traversal attacks (e.g., using '..').
        """
        if not file_path:
            return False

        # 1. Normalize and resolve the path
        resolved_path = os.path.abspath(file_path)
        
        # 2. Check if the resolved path is within the workspace directory
        # This is the standard, robust method for path confinement.
        return resolved_path.startswith(self.workspace_dir)

    # --- Agent-Specific Resource Management ---

    def get_daily_reasoning_count(self) -> int:
        """Returns the remaining reasoning steps for the current day."""
        # Provides a default of 0 if key is missing, although _check_daily_reset should set it.
        return self.resources.get('daily_reasoning_count', 0)

    def record_reasoning_step(self) -> bool:
        """Records a reasoning step, decrementing the count. Returns False if exhausted."""
        current_count = self.get_daily_reasoning_count()
        if current_count > 0:
            new_count = current_count - 1
            self.set_resource('daily_reasoning_count', new_count)
            return True
        return False

    def check_termination_status(self) -> bool:
        """Checks if the Agent has been flagged for termination."""
        return self.resources.get('terminated', False)
    
    def set_terminated(self, status: bool):
        """Flags the Agent for graceful termination."""
        self.set_resource('terminated', status)