import os
from typing import Any, Dict, List
from google import genai
from core.logger import Logger
from core.definitions.models import Action
from core.brain.memory import Memory

class Reason:
    """Serves as the Agents reasoning."""
    def __init__(self, 
                 constants: Dict[str, Any], 
                 logger: Logger,
                 principles: str, 
                 memory: Memory):
        
        self.constants = constants
        self.logger = logger
        self.principles = principles
        self.memory = memory
        self.gemini = Gemini(constants, principles, memory)
    
    def get_next_actions(self, current_action: Action) -> List[Action]:
        # TODO Add local reasoning before elevating to Gemini
        return self.gemini.get_next_actions(current_action)

class Gemini:
    """Handles integration with the Gemini API for the agent's reasoning process."""

    def __init__(self, 
                 constants: Dict[str, Any], 
                 principles: str, 
                 memory: Memory):
        
        self.constants = constants
        self.memory = memory
        self.model_name = self.constants['API']['MODEL']
        self.principles = principles
        
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")
        self.client = genai.Client(api_key=self.api_key)

    def _build_context_prompt(self, current_action: Action) -> str:
        """Constructs the comprehensive prompt for the LLM."""
        # TODO construct the prompt out of agent principles, current_action, and memory
        
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