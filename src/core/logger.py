from typing import Any, Dict, List, Union
from core.definitions.models import LogType, Action
from core.utilities import append_file, current_timestamp, read_file_tail

class Logger:
    """Manages logging and printing to the console"""
    
    def __init__(self, constants: Dict[str, Any]):
        self._constants = constants
        self._log_level = constants['LOG_LEVEL']
        self._log_file = self._constants['FILE_PATHS']['LOG_FILE']

    def _log(self, log_type: LogType, msg: str, action: Union[Action, None] = None):
        if log_type.value > self._log_level:
            return
        
        if action:
            label = f"{log_type.name} - {action.type.name}"
        else:
            label = f"{log_type.name}"

        log_str = f"[{label}]: {msg}"
        print(log_str)

        time_str = current_timestamp()
        file_log_str = f"[{time_str}]{log_str}\n"
        append_file(self._log_file, file_log_str)

    def recent_logs(self) -> List[str]:
        return read_file_tail(self._log_file, self._constants['AGENT']['LOG_TAIL_COUNT'])

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