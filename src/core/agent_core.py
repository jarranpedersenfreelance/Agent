from core.definitions.models import Action
from core.execution.action_handler import ActionHandler
from core.brain.memory import Memory
from core.brain.reason import Reasoner
from typing import Dict, Any

class AgentCore:
    """
    The core loop and orchestration mechanism for the Agent.
    """
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.memory = Memory(constants)
        
        # Initialize components, passing necessary dependencies
        self.reasoner = Reasoner(constants)
        # Pass memory to ActionHandler so it can update file_contents
        self.action_handler = ActionHandler(constants, self.memory) 

    def run(self):
        """
        The main execution loop for the agent.
        """
        print("Starting Agent Core loop...")
        
        while True:
            # 1. Pop the next action
            current_action = self.memory.pop_action()
            
            if not current_action:
                print("Action queue is empty. Agent is entering a NO_OP state.")
                self.memory.add_action(Action(explanation="Action queue empty, performing NO_OP."))
                continue

            # 2. Execute the action
            # The execution logic will be moved to the ActionHandler for REASON, 
            # READ_FILE, and WRITE_FILE.
            try:
                # TODO: Implement action logging here (part of Task 5)
                
                # REASON is special: it generates new actions and adds them to the queue
                if current_action.type.name == 'REASON':
                    new_actions = self.reasoner.process_reasoning(current_action)
                    self.memory.add_actions(new_actions)
                    
                # Other actions are handled by the ActionHandler
                else:
                    self.action_handler.exec_action(current_action)
                
            except Exception as e:
                print(f"ERROR: Failed to execute action {current_action.type.name}: {e}")
                # Optional: Add an action to reason about the failure

            # 3. Save memory state
            self.memory.memorize()