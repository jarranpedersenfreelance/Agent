from typing import Dict, Any
from core.definitions.models import Action

class ActionHandler:
    """
    Manages the execution of actions other than the REASON action.
    """
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants

    def exec_action(self, action: Action) -> str:
        """
        Executes a successfully parsed Action.
        """

        # TODO handle execute different actions (read file, write file, execute) as defined in the models
        
        return ""