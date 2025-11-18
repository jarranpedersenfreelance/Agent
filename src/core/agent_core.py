import os
import traceback
from typing import Dict, Any
import pytest

from core.logger import Logger
from core.utilities import read_file, yaml_dict_load
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
        self._constants = constants
        self._logger = Logger(constants)
        self._agent_principles = read_file(constants['FILE_PATHS']['AGENT_PRINCIPLES_FILE'])
        self._logger.log_info("Initializing AgentCore")
        
        # Initialize Modules
        is_test = True if os.environ.get("AGENT_TEST_MODE") else False
        self._memory = Memory(self._constants, self._logger, is_test)
        self._reason = Reason(self._constants, self._logger, self._agent_principles, self._memory)
        self._action_handler = ActionHandler(self._constants, self._logger, self._memory)

        self._logger.log_info("AgentCore initialized")

    def _debug(self, debug_str: str):
        self._logger.log_warning(debug_str)
        self._logger.log_warning(f"Resetting actions with debug REASON, adding current task to todo")
        self._memory.add_immediate_todo(self._memory.get_thought(self._constants['AGENT']['TASK_THOUGHT']))
        self._memory.reset_actions(
            f"Review logs in memory and debug what went wrong. Implement Fix. Then continue with previous task (now at front of todo list)", 
            debug_str
        )

    def run(self):
        self._logger.log_info("Starting execution loop")
        
        self._memory.set_count(Count.REASON, 0)
        max_steps = self._constants['AGENT']['MAX_REASON_STEPS']

        while True:
            self._memory.load_logs()
            self._memory.memorize()

            action_list = self._memory.list_actions()
            if not action_list:
                self._logger.log_warning("Ran out of actions")
                self._logger.log_info(f"Resetting actions, adding [REASON: Plan] action")
                self._memory.reset_actions("Plan", "action queue was empty")

            # TERMINATE when todo list is empty, but leave last reason action
            todo = self._memory.get_todo_list()
            if not todo:
                last_action = self._memory.pop_last_action()
                self._memory.empty_actions()
                self._memory.add_action(TerminateAction(
                    explanation = "empty todo list"
                ))
                self._memory.add_action(last_action)

            action = self._memory.pop_action()

            try:
                if isinstance(action, TerminateAction):
                    self._logger.log_info("TERMINATE action in queue, Agent terminating")
                    break
                
                elif isinstance(action, ReasonAction):
                    reason_count = self._memory.inc_count(Count.REASON)
                    self._memory.set_thought(self._constants['AGENT']['TASK_THOUGHT'], action.task)
                    
                    if reason_count == max_steps:
                        self._logger.log_info("Reason limit reached, Agent terminating")
                        break

                    self._logger.log_action(action, action.task)
                    new_actions = self._reason.get_next_actions(action)
                    if new_actions:
                        last_action = new_actions[-1]
                        if last_action.type != ActionType.REASON:
                            self._debug("last reason action returned an action list that didn't end with a REASON action")
                        
                        else:
                            self._memory.add_actions(new_actions)
                            self._logger.log_info(f"Queued {len(new_actions)} new actions")
                    else:
                        self._debug("last reason action returned no actions")

                else:
                    self._action_handler.exec_action(action)

            except Exception as e:
                self._logger.log_error(f"Failed to execute action {action.type.name}: {e}")
                self._logger.log_error(f"Stack Trace: {traceback.format_exc()}")
                self._debug(f"failed to execute action {action.type.name}")

    def run_tests(self):
        """Runs all tests and outputs results"""
        test_dir = self._constants['FILE_PATHS']['TEST_DIR']
        report_file = self._constants['FILE_PATHS']['TEST_OUTPUT']
        self._logger.log_info(f"Starting test run in directory: {test_dir}")
        
        if not os.path.isdir(test_dir):
            self._logger.log_error(f"Test directory not found: {test_dir}")
            return
            
        try:
            # Command line arguments for pytest.main():
            # ['--html', REPORT_FILE]: Tells pytest to generate an HTML report at the specified path.
            # ['--self-contained-html']: Ensures the HTML file includes all CSS/JS, making it a single human-readable file.
            pytest_args = [
                test_dir, 
                '--html', report_file, 
                '--self-contained-html'
            ]
            
            exit_code = pytest.main(pytest_args)
            
            # Log the result
            if exit_code == 0:
                self._logger.log_info(f"All tests passed! Report generated at: {report_file}")
            else:
                self._logger.log_warning(f"Tests failed (Exit code: {exit_code}). Report generated at: {report_file}")

        except Exception as e:
            self._logger.log_error(f"Failed to run pytest: {e}")
            self._logger.log_error(f"Stack Trace: {traceback.format_exc()}")
            
        self._logger.log_info("Test run finished.")

# --- Main Entry Point ---
if __name__ == "__main__":
    try:
        constants = yaml_dict_load(CONSTANTS_YAML)
        agent = AgentCore(constants)
        if agent._memory.is_test():
            agent.run_tests()
        else:
            agent.run()

    except Exception as e:
        print(f"Critical error during Agent execution: {e}")
        print(traceback.format_exc())
        os._exit(1)