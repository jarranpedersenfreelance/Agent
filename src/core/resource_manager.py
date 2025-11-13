# src/core/resource_manager.py
import os
from datetime import date
from typing import Any, Dict
from .utilities import yaml_safe_load, yaml_safe_dump, write_text_file

# --- Resource Manager ---

class ResourceManager:
    """Manages file access security and tracks daily resource consumption."""
    
    # Define core state keys that can be accessed/overridden via get/set_resource for testing/management flexibility
    CORE_STATE_KEYS = ['daily_reasoning_count', 'last_run_date'] # FIX: Added for dynamic access
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.state_file = os.path.join(
            "workspace", self.constants['FILE_PATHS']['RESOURCES_STATE_FILE']
        )
        self.workspace_dir = os.path.abspath("workspace")
        self._load_state()

    def _load_state(self):
        """Loads state data from disk, handling file not found by setting defaults."""
        try:
            state = yaml_safe_load(self.state_file)
            # FIX: Ensure last_run_date is converted to date object if loaded from YAML string
            if 'last_run_date' in state and isinstance(state['last_run_date'], str):
                 state['last_run_date'] = date.fromisoformat(state['last_run_date'])
            self.state = state
        except FileNotFoundError:
            self.state = self._get_default_state()
            self._save_state()
        
        # Check and apply daily reset
        self._check_daily_reset()
        
    def _save_state(self):
        """Saves the current state data to disk."""
        # Convert date objects to ISO format string for YAML serialization
        state_to_save = self.state.copy()
        if 'last_run_date' in state_to_save:
            state_to_save['last_run_date'] = state_to_save['last_run_date'].isoformat()
            
        yaml_safe_dump(state_to_save, self.state_file)
        
    def _get_default_state(self) -> Dict[str, Any]:
        """Returns the default state dictionary."""
        return {
            'daily_reasoning_count': self.constants['AGENT']['MAX_REASONING_STEPS'],
            'last_run_date': date.today(),
            'resources': {}
        }

    def _check_daily_reset(self):
        """Resets daily limits if the last run date was yesterday or earlier."""
        today = date.today()
        # Ensure the value being compared is a date object
        last_run_date_obj = self.state['last_run_date']
        
        if last_run_date_obj < today:
            self.state['daily_reasoning_count'] = self.constants['AGENT']['MAX_REASONING_STEPS']
            self.state['last_run_date'] = today
            self._save_state()

    def record_reasoning_step(self) -> bool:
        """Decrements the reasoning count if resources allow."""
        if self.state['daily_reasoning_count'] > 0:
            self.state['daily_reasoning_count'] -= 1
            self._save_state()
            return True
        return False

    def get_daily_reasoning_count(self) -> int:
        """Returns the remaining daily reasoning steps."""
        return self.state['daily_reasoning_count']

    def set_resource(self, key: str, value: Any):
        """
        Sets a persistent resource value. If the key is a core state key, 
        it is set directly on self.state. Otherwise, it is stored in 'resources'.
        """
        if key in self.CORE_STATE_KEYS:
            self.state[key] = value # FIX: Allows test to set core state
        else:
            self.state['resources'][key] = value
        
        self._save_state()

    def get_resource(self, key: str) -> Any:
        """
        Gets a persistent resource value. If the key is a core state key, 
        it is retrieved directly from self.state.
        """
        if key in self.CORE_STATE_KEYS:
            return self.state.get(key) # FIX: Allows test to read core state
        else:
            return self.state['resources'].get(key)
    
    def clear_state(self):
        """Clears all resources and resets the state to defaults."""
        self.state = self._get_default_state()
        self._save_state()
        
    def is_file_path_safe(self, file_path: str) -> bool:
        """
        Verifies that a file path is safe and confined to the workspace directory.
        Denies directory traversal (..), absolute paths outside workspace.
        """
        if not file_path:
            return False
            
        # 1. Resolve the full path
        full_path = os.path.abspath(file_path)
        
        # 2. Check for directory traversal (e.g., /../)
        # Check if traversing up from workspace/ still results in workspace/
        if ".." in file_path:
            if not full_path.startswith(self.workspace_dir):
                return False

        # 3. Check if the path is inside the workspace_dir
        common_path = os.path.commonpath([full_path, self.workspace_dir])

        # If the path is safe, the common path must be the workspace directory itself
        return full_path.startswith(self.workspace_dir)