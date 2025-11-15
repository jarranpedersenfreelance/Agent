import os
from typing import Dict, Any

from core.logger import Logger
from core.utilities import read_file, yaml_safe_load
from core.definitions.models import ActionType, Count, ReasonAction, ReasonActionArgs
from core.brain.memory import Memory
from core.brain.reason import Reason
from core.execution.action_handler import ActionHandler

CONSTANTS_YAML = "core/definitions/agent_constants.yaml"

class AgentCore:
    """
    The main class for the Agent.
    Manages the core loop, initialization, and component orchestration.
    """
    
    def __init__(self, constants: Dict[str, Any], mock = False):
        self.constants = constants
        self.mock = mock
        self.logger = Logger(constants, mock)
        self.agent_principles = read_file(self.constants['FILE_PATHS']['AGENT_PRINCIPLES_FILE'])
        self.logger.log_info("Initializing AgentCore")
        
        # Initialize Modules
        self.memory = Memory(self.constants, self.logger, mock)
        self.reason = Reason(self.constants, self.logger, self.agent_principles, self.memory)
        self.action_handler = ActionHandler(self.constants, self.logger, self.memory)

        self.logger.log_info("AgentCore initialized")

    def run(self):
        self.logger.log_info("Starting execution loop")
        
        self.memory.set_count(Count.REASON, 0)
        max_steps = self.constants['AGENT']['MAX_REASON_STEPS']

        while True:
            self.memory.memorize()
            action = self.memory.pop_action()

            try:
                if not action:
                    self.logger.log_warning("Ran out of actions")
                    self.logger.log_info(f"Queuing Plan action")
                    self.memory.add_action(ReasonAction(
                        type = ActionType.REASON,
                        task = "Plan",
                        explanation = "action queue was empty"
                    ))
                
                elif isinstance(action, ReasonAction):
                    reason_count = self.memory.inc_count(Count.REASON)
                    
                    if reason_count == max_steps:
                        self.logger.log_info("Reason limit reached, Agent terminating")
                        break

                    self.logger.log_action(action, action.arguments.task)
                    new_actions = self.reason.get_next_actions(action)
                    if new_actions:
                        self.memory.add_actions(new_actions)
                        self.logger.log_info(f"Queued {len(new_actions)} new actions")
                    else:
                        self.logger.log_warning("Reason action returned no new actions")
                        self.logger.log_info(f"Queuing Debug action")
                        self.memory.add_action(ReasonAction(
                            type = ActionType.REASON,
                            task = "Debug why last reason action returned no actions",
                            explanation = "reasoning failed to return actions"
                        ))

                else:
                    self.action_handler.exec_action(action)

            except Exception as e:
                self.logger.log_error(f"Failed to execute action {action.type.name}: {e}")
                self.logger.log_info(f"Queuing Debug action")
                self.memory.add_action(ReasonAction(
                    type = ActionType.REASON,
                    task = "Debug why last action failed",
                    explanation = "action failed"
                ))


# --- Main Entry Point ---
if __name__ == "__main__":
    try:
        constants = yaml_safe_load(CONSTANTS_YAML)
        agent = AgentCore(constants)
        agent.run()
    except Exception as e:
        print(f"Critical error during Agent execution: {e}")
        os._exit(1)