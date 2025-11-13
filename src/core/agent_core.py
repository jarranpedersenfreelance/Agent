# src/core/agent_core.py

import time
import os
import signal
from typing import Dict, Any
from core.utilities import read_text_file
from core.agent_constants import FILE_PATHS
from core.models import Action
from core.action_handler import ActionHandler
from core.task_manager import TaskManager 
from core.resource_manager import ResourceManager 
from core.memory_manager import MemoryManager 
from core.reasoning_integration import ReasoningIntegration 
from core.agent_constants import AGENT as AGENT_CONSTANTS

class AgentCore:
    """
    The main class for the Scion Agent.
    Manages the core loop, initialization, and component orchestration.
    """
    
    def __init__(self):
        # 1. Load Constants
        self.constants: Dict[str, Any] = {
            'FILE_PATHS': FILE_PATHS,
            'AGENT': AGENT_CONSTANTS 
        }
        
        # 2. Load Static Principles and Syntax
        self.agent_principles = read_text_file(self.constants['FILE_PATHS']['AGENT_PRINCIPLES_FILE'])
        self.action_syntax = read_text_file(self.constants['FILE_PATHS']['ACTION_SYNTAX_FILE'])
        
        # 3. Initialize Managers (Assuming all managers are present/functional as stubs)
        self.task_manager = TaskManager(self.constants)
        self.resource_manager = ResourceManager(self.constants)
        self.memory_manager = MemoryManager(self.constants)
        
        # 4. Initialize Reasoning and Action Modules
        self.reasoning_integration = ReasoningIntegration(
            constants=self.constants,
            principles=self.agent_principles,
            action_syntax=self.action_syntax,
            memory_manager=self.memory_manager
        )
        self.action_handler = ActionHandler(
            self.memory_manager, 
            self.resource_manager,
            self.task_manager
        )

        # 5. Initialization Complete
        print("AgentCore initialization complete.")

    def run(self):
        """
        Main execution loop for the agent.
        Processes actions from the queue until the queue is empty or Max Reasoning Steps is hit.
        """
        print("AgentCore starting main execution loop...")
        
        # Initialization Check: If the queue is empty at startup, populate it with the initial REASON action.
        if self.task_manager.is_queue_empty():
            starting_task = self.constants['AGENT']['STARTING_TASK']
            initial_reason_action = Action(
                name="REASON", 
                arguments={"task": starting_task},
                raw_text=f"ACTION: REASON(task='{starting_task}')"
            )
            self.task_manager.add_action(initial_reason_action)
            print(f"Action queue initialized with starting task: {starting_task}")
        
        # Main Loop
        current_step = 0
        max_steps = self.constants['AGENT']['MAX_REASONING_STEPS']

        while current_step < max_steps:
            action = self.task_manager.dequeue_action()

            if action is None:
                # If no actions are available, wait a moment and check again
                time.sleep(self.constants['AGENT']['LOOP_SLEEP_SECONDS'])
                continue

            print(f"\n--- STEP {current_step+1} ---")
            print(f"Executing Action: {action.name}")
            
            if action.name == 'REASON':
                # --- Reasoning Action ---
                current_step += 1
                
                if self.resource_manager.is_daily_reasoning_limit_reached():
                    print("Daily reasoning limit reached. Agent entering sleep state.")
                    break
                
                # Call the Reasoning Integration to get the next sequence of actions
                new_actions = self.reasoning_integration.get_next_actions(action)
                
                if new_actions:
                    for new_action in new_actions:
                        self.task_manager.add_action(new_action)
                    print(f"Queued {len(new_actions)} new actions.")
                else:
                    print("Reasoning returned no new actions. Continuing loop.")

            else:
                # --- Direct/External Action Execution ---
                observation = self.action_handler.handle_action(action)
                print(f"Observation: {observation}")

            if current_step >= max_steps:
                print(f"Maximum reasoning steps ({max_steps}) reached. Terminating loop.")
                break

        print("\nAgent finished execution loop.")

# --- Main Entry Point ---
if __name__ == "__main__":
    try:
        agent = AgentCore()
        agent.run()
    except Exception as e:
        print(f"Critical error during Agent execution: {e}")
        # Signal the container management system that the agent has failed
        os._exit(1)