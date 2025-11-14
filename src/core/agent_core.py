import os
from typing import Dict, Any

from core.utilities import read_text_file, yaml_safe_load
from core.execution.task_manager import TaskManager 
from core.execution.reasoning import Brain
from core.data_management.memory_manager import MemoryManager

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
        self.action_syntax = read_text_file(self.constants['FILE_PATHS']['ACTION_SYNTAX_FILE'])
        
        # Initialize Modules
        self.task_manager = TaskManager(self.constants)
        self.memory_manager = MemoryManager(self.constants)
        self.brain = Brain(self.constants, self.agent_principles, self.memory_manager)

        print("AgentCore initialized.")

    def run(self):
        print("Starting execution loop.")
        
        current_step = 0
        max_steps = self.constants['AGENT']['MAX_REASONING_STEPS']

        while current_step < max_steps:
            action = self.task_manager.dequeue_action()
            
            if action.name == 'REASON':
                current_step += 1
                
                if self.resource_manager.is_daily_reasoning_limit_reached():
                    print("Daily reasoning limit reached. Agent terminating.")
                    break

                print("THINKING: " + action.raw_text)
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