# src/core/agent_core.py
import sys 
import time
import os
import signal
from .utilities import yaml_safe_load, read_text_file
from .resource_manager import ResourceManager 
from .memory_manager import MemoryManager
from .task_manager import TaskManager
from .action_handler import ActionHandler

CONSTANTS_PATH = os.path.join(os.path.dirname(__file__), 'agent_constants.yaml')
PRINCIPLES_PATH = os.path.join(os.path.dirname(__file__), 'agent_principles.txt') # FIX: New principles file

def load_constants(path: str) -> dict:
    """ 
    Loads all constants from the YAML file, returning the structured dictionary.
    """
    try:
        # FIX: Removed constant flattening. Returns nested dict for structured access.
        raw_constants = yaml_safe_load(path) 
        if not raw_constants:
            return {}
        return raw_constants
        
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Constants file not found at {path}")
        sys.exit(1)
    except Exception as e:
        print(f"CRITICAL ERROR: Error loading or decoding constants YAML: {e}")
        sys.exit(1)

def load_agent_principles(path: str) -> str:
    """Loads the core principles/instructions for the agent."""
    try:
        return read_text_file(path)
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Agent principles file not found at {path}")
        sys.exit(1)
    except Exception as e:
        print(f"CRITICAL ERROR: Error reading agent principles: {e}")
        sys.exit(1)


class AgentCore:
    """The main control loop and central brain of the Scion Agent."""
    
    def __init__(self):
        """Initializes constants and core managers."""
        # 1. Load Constants and Configuration
        self.constants = load_constants(CONSTANTS_PATH)
        self.principles = load_agent_principles(PRINCIPLES_PATH)
        
        # Access structured constants
        self.AGENT_CONSTANTS = self.constants.get('AGENT', {})
        self.FILE_CONSTANTS = self.constants.get('FILE_PATHS', {})
        
        # 2. Initialize Managers
        self.resource_manager = ResourceManager(self.constants)
        self.memory_manager = MemoryManager(self.constants)
        self.task_manager = TaskManager(self.constants)
        self.action_handler = ActionHandler(self.constants, 
                                            self.memory_manager, 
                                            self.resource_manager, 
                                            self.task_manager)

        # 3. Setup Signal Handling for clean shutdown
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum, frame):
        """Handles OS signals for clean shutdown."""
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        # Add cleanup logic here if needed
        sys.exit(0)

    def run(self):
        """The main execution loop of the Agent."""
        print("Starting Agent execution loop...")
        
        # Dummy loop placeholder
        while True:
            # 1. Perception/Input (Read Task, Check Queue, etc.)
            # 2. Reasoning (Call Gemini for next action)
            # 3. Action (Execute proposed action)
            # 4. State Update (Log actions, Save memory/resource state)
            # 5. Sleep/Throttle
            
            print("Agent loop cycle completed (Placeholder). Sleeping...")
            time.sleep(self.AGENT_CONSTANTS.get('LOOP_SLEEP_SECONDS', 1)) 


def main():
    """Entry point for the agent."""
    try:
        agent = AgentCore()
        agent.run()
    except Exception as e:
        print(f"CRITICAL UNCAUGHT EXCEPTION: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()