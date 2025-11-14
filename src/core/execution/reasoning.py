import os
from typing import Any, Dict, List, Union
from google import genai
from google.genai import types
from pydantic import ValidationError
from core.definitions.models import Action

class Brain:
    """Serves as the Agents reasoning."""
    def __init__(self, 
                 constants: Dict[str, Any], 
                 principles: str, 
                 memory_manager: Any):
        
        self.constants = constants
        self.gemini = Gemini(constants, principles, memory_manager)
    
    def get_next_actions(self, current_action: Action) -> List[Action]:
        # TODO Add local reasoning before elevating to Gemini

        return self.gemini.get_next_action(current_action)

class Gemini:
    """Handles integration with the Gemini API for the agent's reasoning process."""

    def __init__(self, 
                 constants: Dict[str, Any], 
                 principles: str, 
                 memory_manager: Any):
        
        self.constants = constants
        self.memory_manager = memory_manager
        self.model_name = self.constants['API']['MODEL']
        self.agent_principles = principles
        
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")
        self.client = genai.Client(api_key=self.api_key)

    def _build_context_prompt(self, current_action: Action) -> str:
        """Constructs the comprehensive prompt for the LLM."""
        # TODO construct the prompt out of reasoning principles, current_action, and memory
        
        return ""

    def get_next_actions(self, current_action: Action) -> List[Action]:
        """
        Calls the Gemini API to get the next list of actions.
        """
        # TODO use the constructed prompt to get the next list of actions from Gemini
        # make sure to make Gemini return results in the specified format so it can be parsed
        # actions should be restricted to those that are defined, in the format defined
        # the provided list should always end with a REASON action

        return []