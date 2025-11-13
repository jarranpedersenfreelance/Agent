import os
# REMOVED: import yaml
# FIX: Changed to relative import (from .utilities) and corrected 'load_yaml' to 'yaml_load'.
from .utilities import yaml_load, yaml_dump

class ResourceManager:
    def __init__(self, constants):
        """Initializes the Resource Manager."""
        self.constants = constants
        
        # State file path
        self.state_file_path = self.constants['RESOURCES_STATE_FILE']
        
        # Initialize or load state
        self.resources = self._load_state()

    def _load_state(self):
        """Loads the resource state from the YAML file, or returns a default structure."""
        try:
            # FIX: Changed load_yaml to the correct function name yaml_load
            state = yaml_load(self.state_file_path)
            if state is None:
                # Handle empty file case
                return {}
            return state
        except FileNotFoundError:
            print(f"INFO: Resource state file not found at {self.state_file_path}. Initializing with empty state.")
            return {}
        except Exception as e:
            print(f"ERROR: Failed to load resource state from {self.state_file_path}: {e}")
            return {}

    def _save_state(self):
        """Saves the current resource state to the YAML file."""
        try:
            yaml_dump(self.resources, self.state_file_path)
        except Exception as e:
            print(f"ERROR: Failed to save resource state to {self.state_file_path}: {e}")
            
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