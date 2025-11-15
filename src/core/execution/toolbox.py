import importlib
from typing import Any, Dict
from core.logger import Logger
from core.brain.memory import Memory

class Tool:
    def __init__(self, constants: Dict[str, Any], logger: Logger, memory: Memory):
        self.constants = constants
        self.logger = logger
        self.memory = memory

    def run(self, args: Dict[str, Any]):
        pass


class ToolBox:
    """Manages the execution of tools for the Agent."""
    def __init__(self, constants: Dict[str, Any], logger: Logger, memory: Memory):
        self.constants = constants
        self.logger = logger
        self.memory = memory

    def run_tool(self, module_path: str, tool_class: str, args: Dict[str, Any]):
        module = importlib.import_module(module_path)
        if not module: 
            raise ValueError("RUN_TOOL tried to run a tool module that doesn't exist.")
        tool = getattr(module, tool_class)
        if tool and isinstance(tool, Tool):
            tool.run(args)
        else:
            raise ValueError("RUN_TOOL tried to run a tool class that doesn't exist.")