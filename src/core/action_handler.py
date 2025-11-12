import os
import time
import zipfile
import subprocess
import re
from typing import List, Dict, Any, Optional

from . import agent_constants as constants
from .utilities import load_file_content

# Type hint stubs for managers (Issue 10)
class TaskManagerStub:
    def clear_immediate_task(self) -> bool: pass
class MemoryManagerStub:
    def update_known_files(self, new: List[str], deleted: List[str]): pass

class ActionHandler:
    """Handles the execution of a parsed action.""" # Simplified docstring (Issue 10)
    
    def __init__(self, agent_root: str = constants.FILE_PATHS.ROOT, 
                 task_manager: TaskManagerStub = None,
                 memory_manager: MemoryManagerStub = None):
        self.agent_root = agent_root
        self.task_manager = task_manager
        self.memory_manager = memory_manager
        
        # Issue 1: Dictionary mapping for cleaner execution
        self._action_map = {
            "READ_FILE": self._read_file,
            "WRITE_FILE": self._write_file,
            "SLUMBER": self._slumber,
            "CREATE_DEBUG_SNAPSHOT": self._create_debug_snapshot,
            "RUN_COMMAND": self._run_command,
            "NEXT_TASK": self._next_task,
            "UPDATE_FILE_LIST": self._update_file_list,
        }

    def _log_action(self, action_type: str, args: List[str], result: str):
        """Logs the executed action to the action log file."""
        log_path = os.path.join(self.agent_root, constants.FILE_PATHS.ACTION_LOG_FILE)
        with open(log_path, 'a') as f:
            f.write(f"ACTION: {action_type} ARGS: {args} RESULT: {result}\n")

    def _parse_action_line(self, action_line: str) -> Optional[Dict[str, Any]]:
        """Parses the raw text output from the LLM into an action type and arguments."""
        action_line = action_line.strip()
        
        match = re.match(r"^([A-Z_]+):\s*(.*)$", action_line)

        if match:
            action_type = match.group(1).strip()
            arg_string = match.group(2).strip()
            
            # Issue 8: Simplified parsing for multi-word arguments (WRITE_FILE and RUN_COMMAND)
            if action_type in ["WRITE_FILE", "RUN_COMMAND"]:
                # First word is filename/command, rest is content/full command
                parts = arg_string.split(' ', 1)
                args = parts if len(parts) == 2 else [parts[0], ""]
            else:
                args = [arg for arg in arg_string.split() if arg]
                
            return {"type": action_type, "args": args}
        
        return None

    # --- Core Actions ---

    def _read_file(self, args: List[str]) -> str:
        """Reads the content of a specified file."""
        if not args:
            return "Error: READ_FILE requires a filename argument."
            
        path = os.path.join(self.agent_root, args[0])
        content = load_file_content(path, default_content=f"Error: File '{args[0]}' not found.")
        return content

    def _write_file(self, args: List[str]) -> str:
        """Writes content to a specified file, creating it if it doesn't exist."""
        if len(args) < 2:
            return "Error: WRITE_FILE requires a filename and content argument."
            
        filename = args[0]
        content = args[1]
        path = os.path.join(self.agent_root, filename)
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w') as f:
                f.write(content)
            return f"Success: Content written to '{filename}'."
        except Exception as e:
            return f"Error: Failed to write to '{filename}': {e}"
            
    def _slumber(self, args: List[str]) -> str:
        """Puts the agent to sleep for a specified number of seconds."""
        try:
            sleep_time = float(args[0]) if args else constants.AGENT.LOOP_SLEEP_SECONDS * 5
            sleep_time = max(0.1, sleep_time)
            time.sleep(sleep_time)
            return f"Success: Slumbered for {sleep_time:.2f} seconds."
            
        except ValueError:
            return "Error: SLUMBER argument must be a number representing seconds."
        except Exception as e:
            return f"Error during slumber: {e}"

    def _create_debug_snapshot(self, args: List[str]) -> str:
        """Creates a zip archive of the data/ folder and key state files for debugging."""
        
        default_filename = f"debug_snapshot_{int(time.time())}.zip"
        output_filename = args[0] if args else default_filename
        
        data_dir = os.path.join(self.agent_root, constants.FILE_PATHS.DATA)
        root_files = [
            constants.FILE_PATHS.IMMEDIATE_TASK_FILE,
            constants.FILE_PATHS.GOAL_FILE,
            constants.FILE_PATHS.REASONING_PRINCIPLES_FILE,
            constants.FILE_PATHS.RESOURCES_STATE_FILE, 
            constants.FILE_PATHS.ACTION_LOG_FILE,
        ]

        try:
            with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(data_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        archive_path = os.path.relpath(full_path, self.agent_root)
                        zf.write(full_path, archive_path)

                for relative_path in root_files:
                    full_path = os.path.join(self.agent_root, relative_path)
                    if os.path.exists(full_path):
                        zf.write(full_path, relative_path)
                        
            return f"Success: Debug snapshot created at '{output_filename}'."
            
        except Exception as e:
            return f"Error creating debug snapshot: {e}"

    # --- Utility Actions ---

    def _format_command_output(self, command: str, result: subprocess.CompletedProcess) -> str:
        """Formats and truncates the output of a shell command (Issue 9)."""
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
            
        output = f"Command: {command}\n"
        if result.returncode == 0:
            output += f"Success (Return Code: 0).\nSTDOUT:\n{stdout}"
        else:
            output += f"Execution Failed (Return Code: {result.returncode}).\nSTDERR:\n{stderr}"
            
        # Truncate output if too long
        max_len = constants.AGENT.CONTEXT_TRUNCATION_LIMIT * 2
        if len(output) > max_len:
                output = output[:max_len] + "\n...[OUTPUT TRUNCATED]"
                
        return output

    def _run_command(self, args: List[str]) -> str:
        """Executes a shell command and returns the result."""
        if not args:
            return "Error: RUN_COMMAND requires a command argument."

        command = args[1] if len(args) > 1 else args[0] # Takes the full command string
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.agent_root,
                timeout=30
            )
            return self._format_command_output(command, result)

        except FileNotFoundError:
            return f"Error: Command '{command.split()[0]}' not found (e.g., command name typo)."
        except subprocess.TimeoutExpired:
            return f"Error: Command '{command}' timed out after 30 seconds."
        except Exception as e:
            return f"Execution Error: {e}"
            
    def _next_task(self, args: List[str]) -> str:
        """Clears the immediate task, signaling the agent to advance its goal/plan."""
        if self.task_manager and self.task_manager.clear_immediate_task():
            return "Success: Cleared immediate_task.txt. Agent should now proceed to the next step in its plan."
        return "Error: Failed to clear immediate_task.txt. TaskManager not initialized or file I/O failed."

    def _update_file_list(self, args: List[str]) -> str:
        """Updates the list of known files in memory."""
        if not self.memory_manager:
            return "Error: MemoryManager not initialized."
            
        new_files = []
        deleted_files = []
        
        # Args is a list of space-separated file paths/commands
        for arg in args:
            if arg.startswith('+'):
                new_files.append(arg[1:])
            elif arg.startswith('-'):
                deleted_files.append(arg[1:])
            else:
                new_files.append(arg)

        self.memory_manager.update_known_files(new_files=new_files, deleted_files=deleted_files)
        
        return f"Success: Updated file list. Added {len(new_files)} files, removed {len(deleted_files)} files."

    def execute_action(self, action_type: str, args: List[str], log: bool = True) -> str:
        """
        Executes the specified action based on the action type. (Issue 1)
        """
        handler = self._action_map.get(action_type)

        if handler:
            result = handler(args)
        else:
            result = f"Error: Action '{action_type}' is not yet implemented or is unknown."
            
        if log:
            self._log_action(action_type, args, result)
            
        return result