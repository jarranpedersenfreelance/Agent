import os
import traceback
from typing import Dict, Any

from core.logger import Logger
from core.utilities import read_file, yaml_safe_load
from core.definitions.models import Count, ReasonAction, TerminateAction, ActionType
from core.brain.memory import Memory
from core.brain.reason import Reason
from core.execution.action_handler import ActionHandler

CONSTANTS_YAML = "core/definitions/agent_constants.yaml"

class AgentCore:
    """
    The main class for the Agent.
    Manages the core loop, initialization, and component orchestration.
    """
    
    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.logger = Logger(constants)
        self.agent_principles = read_file(self.constants['FILE_PATHS']['AGENT_PRINCIPLES_FILE'])
        self.logger.log_info("Initializing AgentCore")
        
        # Initialize Modules
        is_test = True if os.environ.get("AGENT_TEST_MODE") else False
        self.memory = Memory(self.constants, self.logger, is_test)
        self.reason = Reason(self.constants, self.logger, self.agent_principles, self.memory)
        self.action_handler = ActionHandler(self.constants, self.logger, self.memory)

        self.logger.log_info("AgentCore initialized")

    def _debug(self, debug_str: str):
        self.logger.log_warning(debug_str)
        self.logger.log_warning(f"Resetting actions with debug REASON, adding current task to todo")
        self.memory.add_immediate_todo(self.memory.get_thought(self.constants['AGENT']['TASK_THOUGHT']))
        self.memory.reset_actions(
            f"Review logs in memory and debug what went wrong. Implement Fix. Then continue with previous task (now at front of todo list)", 
            debug_str
        )

    def run(self):
        self.logger.log_info("Starting execution loop")
        
        self.memory.set_count(Count.REASON, 0)
        max_steps = self.constants['AGENT']['MAX_REASON_STEPS']

        while True:
            self.memory.load_logs()
            self.memory.memorize()

            # TERMINATE when todo list is empty, but leave last reason action
            todo = self.memory.get_todo_list()
            if not todo:
                last_action = self.memory.pop_last_action()
                self.memory.empty_actions()
                self.memory.add_action(TerminateAction(
                    explanation = "empty todo list"
                ))
                self.memory.add_action(last_action)

            action = self.memory.pop_action()

            try:
                if not action:
                    self.logger.log_warning("Ran out of actions")
                    self.logger.log_info(f"Resetting actions, adding [REASON: Plan] action")
                    self.memory.reset_actions("Plan", "action queue was empty")

                elif isinstance(action, TerminateAction):
                    self.logger.log_info("TERMINATE action in queue, Agent terminating")
                    break
                
                elif isinstance(action, ReasonAction):
                    reason_count = self.memory.inc_count(Count.REASON)
                    self.memory.set_thought(self.constants['AGENT']['TASK_THOUGHT'], action.task)
                    
                    if reason_count == max_steps:
                        self.logger.log_info("Reason limit reached, Agent terminating")
                        break

                    self.logger.log_action(action, action.task)
                    new_actions = self.reason.get_next_actions(action)
                    if new_actions:
                        last_action = new_actions[-1]
                        if last_action.type != ActionType.REASON:
                            self._debug("last reason action returned an action list that didn't end with a REASON action")
                        
                        else:
                            self.memory.add_actions(new_actions)
                            self.logger.log_info(f"Queued {len(new_actions)} new actions")
                    else:
                        self._debug("last reason action returned no actions")

                else:
                    self.action_handler.exec_action(action)

            except Exception as e:
                self.logger.log_error(f"Failed to execute action {action.type.name}: {e}")
                self.logger.log_error(f"Stack Trace: {traceback.format_exc()}")
                self._debug(f"failed to execute action {action.type.name}")

    def run_tests(self):
        pass

# --- Main Entry Point ---
if __name__ == "__main__":
    try:
        constants = yaml_safe_load(CONSTANTS_YAML)
        agent = AgentCore(constants)
        if agent.memory.is_test():
            agent.run_tests()
        else:
            agent.run()

    except Exception as e:
        print(f"Critical error during Agent execution: {e}")
        print(traceback.format_exc())
        os._exit(1)