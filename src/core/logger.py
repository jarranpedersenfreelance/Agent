from typing import Any, Dict
from datetime import datetime, timezone
from core.definitions.models import LogType, Action
from core.utilities import append_file

class Logger:
    """Manages logging and printing to the console"""
    
    def __init__(self, constants: Dict[str, Any], mock: bool = False):
        self.constants = constants
        self.log_level = constants['LOG_LEVEL']

        if not mock:
            self.log_file = self.constants['FILE_PATHS']['LOG_FILE']
        else:
            self.log_file = self.constants['FILE_PATHS']['TEST_LOG_FILE']

    def _log(self, log_type: LogType, msg: str, action: Action = None):
        if log_type.value > self.log_level:
            return
        
        if action:
            label = f"{log_type.name} - {action.type.name}"
        else:
            label = f"{log_type.name}"

        log_str = f"[{label}]: {msg}"
        print(log_str)

        time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        timed_log_str = f"[{time_str}]{log_str}"
        append_file(self.log_file, timed_log_str)

    def log_error(self, msg: str):
        self._log(LogType.ERROR, msg)

    def log_warning(self, msg: str):
        self._log(LogType.WARNING, msg)
    
    def log_action(self, action: Action, msg: str):
        self._log(LogType.ACTION, msg, action)

    def log_info(self, msg: str):
        self._log(LogType.INFO, msg)

    def log_debug(self, msg: str):
        self._log(LogType.DEBUG, msg)