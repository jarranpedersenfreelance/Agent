import os
from typing import Dict, Any

from core.utilities import read_text_file, yaml_safe_load
from core.execution.task_manager import TaskManager 
from core.execution.brain import Brain
from core.data_management.memory_manager import MemoryManager
from core.definitions.models import Action_Type

CONSTANTS_YAML = "core/definitions/agent_constants.yaml"

class AgentCore:
    """
    The main class for the Agent.
    Manages the core loop, initialization, and component orchestration.
    """
    
    def __init__(self):
        print("Initializing AgentCore...")

        # Initialize Data Variables
        self.constants: Dict[str, Any] = yaml_safe_load(CONSTANTS_YAML)
        self.agent_principles = read_text_file(self.constants['FILE_PATHS']['AGENT_PRINCIPLES_FILE'])
        
        # Initialize Modules
        self.memory_manager = MemoryManager(self.constants)
        self.task_manager = TaskManager(self.constants, self.memory_manager)
        self.brain = Brain(self.constants, self.agent_principles, self.memory_manager)

        print("AgentCore initialized.")

    def run(self):
        print("Starting execution loop.")
        
        self.memory_manager.reset_reasoning_count()
        max_steps = self.constants['AGENT']['MAX_REASONING_STEPS']

        while self.memory_manager.get_reasoning_count() < max_steps:
            action = self.task_manager.dequeue_action()
            
            if action.type == Action_Type.REASON:
                self.memory_manager.inc_reasoning_count()
                
                if self.memory_manager.get_reasoning_count() == max_steps:
                    print("Daily reasoning limit reached. Agent terminating.")
                    break

                print("THINKING: " + str(action.arguments))
                new_actions = self.brain.get_next_actions(action)
                if new_actions:
                    self.task_manager.add_actions(new_actions)
                    print(f"Queued {len(new_actions)} new actions.")
                else:
                    print("Reasoning returned no new actions. Critical failure. Agent terminating")
                    break

            else:
                observation = self.action_handler.exec_action(action)
                print(f"Observation: {observation}")

        print("\nAgent finished execution loop.")

# --- Main Entry Point ---
if __name__ == "__main__":
    try:
        agent = AgentCore()
        agent.run()
    except Exception as e:
        print(f"Critical error during Agent execution: {e}")
        os._exit(1)