# src/core/action_handler.py

from typing import Dict, Any, Optional
from core.models import Action 
from core.utilities import read_text_file
from core.agent_constants import FILE_PATHS

class ActionHandler:
    """
    Manages the parsing, execution, and queuing of actions proposed by the LLM.
    This implements the core logic for translating the LLM's text output into executable steps.
    """
    # NOTE: memory_manager, resource_manager, and task_manager are passed for future growth
    def __init__(self, memory_manager, resource_manager, task_manager):
        self.memory_manager = memory_manager
        self.resource_manager = resource_manager
        self.task_manager = task_manager
        
        # Load the action syntax to guide parsing
        self.action_syntax = read_text_file(FILE_PATHS['ACTION_SYNTAX_FILE'])
        
    def parse_action(self, raw_action_text: str) -> Optional[Action]:
        """
        Parses the raw text output from the LLM into an Action object.
        Expected format: ACTION: ActionName(arg1='value1', arg2='value2')
        """
        raw_action_text = raw_action_text.strip()
        
        if not raw_action_text.startswith("ACTION:"):
            # Not a formal action command
            return None

        try:
            # Clean up the raw text to isolate the function call part
            action_call = raw_action_text.replace("ACTION:", "", 1).strip()
            
            # Find the action name and arguments string
            name_end = action_call.find('(')
            if name_end == -1:
                 # Case: ACTION: NO_OP
                 name = action_call.strip()
                 args_str = ""
            else:
                # Case: ACTION: ACT(key='value')
                name = action_call[:name_end].strip()
                args_str = action_call[name_end+1:-1].strip()
            
            arguments: Dict[str, Any] = {}
            if args_str:
                # Basic argument parsing: ASSUME KEY='VALUE' or KEY="VALUE"
                arg_pairs = args_str.split(',')
                for pair in arg_pairs:
                    if not pair.strip(): continue
                    try:
                        key, value = pair.split('=', 1)
                        # Basic cleanup: trim whitespace and quotes from keys/values
                        k = key.strip().strip("'\"")
                        v = value.strip().strip("'\"")
                        arguments[k] = v
                    except ValueError:
                        # Skip bad pair for this initial, fragile parser
                        continue

            return Action(name=name, arguments=arguments, raw_text=raw_action_text)

        except Exception as e:
            # Fail gracefully on unparsable input
            return None

    def execute_action(self, action: Action) -> str:
        """
        Executes a successfully parsed Action. Implements the two simplest required actions.
        """
        
        if action.name == 'NO_OP':
            action.success = True
            observation = "Action NO_OP executed successfully. This is a null action."
        elif action.name == 'ACTION_PROPOSAL':
            # This action signals the end of a self-update cycle.
            action.success = True
            observation = "Action Proposal logged. Waiting for Architect to deploy changes."
        else:
            action.success = False
            observation = f"ERROR: Action '{action.name}' is not yet implemented in the core ActionHandler."
            
        return observation
        
    def handle_action(self, action: Action) -> str:
        """Processes an incoming Action (from TM or RI) and executes it."""
        
        # 1. Log action to memory (Placeholder)
        
        # 2. Execute Action
        observation = self.execute_action(action)
        
        # 3. Log observation (Placeholder)
        
        return observation