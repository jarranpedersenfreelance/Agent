# src/core/constants.py
import yaml
import os
import sys
from typing import Dict, Any

# These global objects will hold the constants after load_constants is called.
FILE_PATHS: Dict[str, str] = {}
API: Dict[str, Any] = {}
AGENT: Dict[str, Any] = {}
CONSTANTS_FILE = "agent_constants.yaml"

# Utility class for dictionary access as attributes (like AGENT.MAX_REASONING_STEPS)
class DotAccess(dict):
    """A dictionary that allows accessing keys as attributes."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    def __setattr__(self, key, value):
        self[key] = value
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

def load_constants(base_path: str = os.path.dirname(__file__)):
    """Loads constants from the YAML file into the global objects."""
    global FILE_PATHS, API, AGENT
    
    yaml_path = os.path.join(base_path, CONSTANTS_FILE)
    
    # Simple direct file load without using utilities.py to avoid circular dependency
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            constants = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Constants file not found at {yaml_path}")
        # Terminate immediately if core configuration is missing
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"CRITICAL ERROR: Error decoding constants YAML: {e}")
        sys.exit(1)

    # Convert the dicts to DotAccess objects for easy attribute-style access
    FILE_PATHS = DotAccess(constants.get('FILE_PATHS', {}))
    API = DotAccess(constants.get('API', {}))
    AGENT = DotAccess(constants.get('AGENT', {}))

# Expose all necessary names
__all__ = ['FILE_PATHS', 'API', 'AGENT', 'load_constants']