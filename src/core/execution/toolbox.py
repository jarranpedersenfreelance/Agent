import importlib
from typing import Any, Dict
from core.logger import Logger
from core.brain.memory import Memory

class Tool:
    def __init__(self, constants: Dict[str, Any], logger: Logger, memory: Memory):
        self._constants = constants
        self._logger = logger
        self._memory = memory

    def run(self, args: Dict[str, Any] = {}) -> str:
        return ""


class ToolBox:
    """Manages the execution of tools for the Agent."""
    def __init__(self, constants: Dict[str, Any], logger: Logger, memory: Memory):
        self._constants = constants
        self._logger = logger
        self._memory = memory

    def run_tool(self, module_str: str, tool_class: str, args: Dict[str, Any]):
        module = importlib.import_module(module_str)
        if not module: 
            raise ValueError("RUN_TOOL tried to run a tool module that doesn't exist.")
        
        tool = getattr(module, tool_class)
        if tool and issubclass(tool, Tool):
            tool_instance = tool(self._constants, self._logger, self._memory)
            output = tool_instance.run(args)
            self._memory.set_thought(self._constants['AGENT']['TOOL_OUTPUT_THOUGHT'], output)
                
        else:
            raise ValueError("RUN_TOOL tried to run a tool class that doesn't exist.")