import sys
import time
import os
import signal
from .utilities import yaml_load # Assuming this is the correct utility function
from .resource_manager import ResourceManager
# Add other managers here as they are developed:
# from .memory_manager import MemoryManager
# from .task_manager import TaskManager
# from .action_handler import ActionHandler


CONSTANTS_PATH = os.path.join(os.path.dirname(__file__), 'agent_constants.yaml')

def load_constants(path: str) -> dict:
    """
    Loads all constants from the YAML file, flattening the nested sections
    into a single dictionary for easy access by managers.
    """
    try:
        raw_constants = yaml_load(path)
        if not raw_constants:
            return {}
        
        constants = {}
        # Iterate through the top-level keys (FILE_PATHS, API, AGENT) and flatten them
        for key, value in raw_constants.items():
            if isinstance(value, dict):
                constants.update(value)
            else:
                # Handle any potential top-level constants
                constants[key] = value
                
        return constants
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load or flatten constants from {path}: {e}")
        # Terminate immediately if constants cannot be loaded
        sys.exit(1)


class AgentCore:
    def __init__(self):
        """Initializes the Agent Core and its components."""
        
        # 1. Load Constants
        self.constants = load_constants(CONSTANTS_PATH)
        if not self.constants:
            print("CRITICAL ERROR: Constants are empty. Agent cannot proceed.")
            sys.exit(1)

        # 2. Initialize Managers
        try:
            # All managers must be initialized with the flattened constants dictionary
            self.resource_manager = ResourceManager(self.constants)
            
            # self.memory_manager = MemoryManager(self.constants)
            # self.task_manager = TaskManager(self.constants)
            # self.action_handler = ActionHandler(self.constants, self.memory_manager, self.resource_manager, self.task_manager)
            
            print("✅ Agent Core initialized successfully.")
            
        except Exception as e:
            # This is the error seen in the logs
            print(f"CRITICAL ERROR: Failed to initialize one or more core managers: {e}")
            sys.exit(1)
            
        # Register signal handlers for clean shutdown
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
            time.sleep(self.constants.get('LOOP_SLEEP_SECONDS', 1)) # Default to 1 second if constant is missing

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