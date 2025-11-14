import os
from typing import Dict, Any

from core.utilities import read_text_file, yaml_safe_load
from core.definitions.models import Action_Type, Count
from core.brain.memory import Memory
from core.brain.reason import Reason
from core.execution.action_handler import ActionHandler

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
        self.memory = Memory(self.constants)
        self.reason = Reason(self.constants, self.agent_principles, self.memory)
        self.action_handler = ActionHandler(self.constants)

        print("AgentCore initialized.")

    def run(self):
        print("Starting execution loop...")
        
        self.memory.set_count(Count.REASONING, 0)
        max_steps = self.constants['AGENT']['MAX_REASONING_STEPS']

        while self.memory.get_count(Count.REASONING) < max_steps:
            self.memory.memorize()
            action = self.memory.pop_action()
            
            if action.type == Action_Type.REASON:
                reason_count = self.memory.inc_count(Count.REASONING)
                
                if reason_count == max_steps:
                    print("Daily reasoning limit reached. Agent terminating...")
                    break

                print("THINKING: " + action.arguments['task'])
                new_actions = self.reason.get_next_actions(action)
                if new_actions:
                    self.memory.add_actions(new_actions)
                    print(f"Queued {len(new_actions)} new actions.")
                else:
                    print("Reasoning returned no new actions. Agent terminating...")
                    break

            else:
                observation = self.action_handler.exec_action(action)
                print(f"Observation: {observation}")

        print("Agent finished execution loop.")

# --- Main Entry Point ---
if __name__ == "__main__":
    try:
        agent = AgentCore()
        agent.run()
    except Exception as e:
        print(f"Critical error during Agent execution: {e}")
        os._exit(1)