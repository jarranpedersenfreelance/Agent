from typing import Any, Dict, List, Union
from core.definitions.models import LogType, Action
from core.utilities import append_file, current_timestamp, read_file_tail, get_file_size, read_file_lines, write_file

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

        # delete old logs if max size reached (half of max size)
        current_size = get_file_size(self._log_file)
        max_size = int(self._constants['RESOURCE_CAPS']['LOG_SIZE'])
        if current_size >= max_size:
            target_size = int(max_size / 2)
            remaining_lines = read_file_lines(self._log_file)
            while current_size > target_size:
                removed_log = remaining_lines.pop(0)
                line_size = len(removed_log.encode())
                current_size -= line_size

            remaining_lines.append(f"[{time_str}][{LogType.WARNING.name}]: Max log file size reached, removed oldest logs\n")
            write_file(self._log_file, ''.join(remaining_lines))

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