# src/secondary/action_handler.py

import os
import re
import subprocess
from typing import Any

# CRITICAL FIX: Define files that are considered "core" and require Architectural Review for modification.
# These paths must match the file paths relative to the workspace run directory.
CORE_FILES = ["src/core/goal.txt", "src/core/agent_core.py"] 

class ActionHandler:
    """
    Handles the parsing and low-level execution of file I/O and shell commands.
    Designed to be the base for the core ExecutionLayer.
    """
    def __init__(self, agent: Any):
        # The agent instance is required to access the memory stream for logging observations.
        self.agent = agent
        # Optimized regex for parsing actions
        # Group 1: Action Type (e.g., WRITE_FILE), Group 2: The rest of the content
        self.action_pattern = re.compile(r"(\w+):\s*(.*?)(?:\n|$)", re.DOTALL)
        
    # --- Parsing and Review Check ---

    def parse_action(self, raw_action: str) -> tuple[str, str, str]:
        """
        Parses a raw action string into structured components (type, target, content).
        """
        match = self.action_pattern.match(raw_action.strip())
        
        if not match:
            return "UNKNOWN", "", ""

        action_type = match.group(1).upper()
        content_raw = match.group(2).strip()
        
        # For actions that involve content (WRITE_FILE, etc.), separate path (target) from content
        if action_type in ["GENERATE_FILE", "MODIFY_FILE", "WRITE_FILE"]:
            parts = content_raw.split('\n', 1)
            target = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            return action_type, target, content
        
        # For other actions (READ_FILE, RUN_COMMAND, SLUMBER, ASK_USER_QUESTION)
        return action_type, content_raw, ""

    def handle_action(self, raw_action: str) -> tuple[str, str, str, str]:
        """
        Processes a raw action string, determines if it requires Architectural Review.
        Returns a tuple (action_type, target, content, status_message).
        """
        action_type, target, content = self.parse_action(raw_action)
        
        # CRITICAL CHECK: Does the target require Architect Review?
        if action_type in ["GENERATE_FILE", "MODIFY_FILE", "WRITE_FILE"]:
            # Check if the target is one of the read-only core files
            if target in CORE_FILES:
                status_message = "ARCHITECT_REVIEW_REQUIRED"
                return action_type, target, content, status_message
        
        # All other valid actions are passed through for execution in the core layer
        status_message = "PROCEED_TO_EXECUTION"
        return action_type, target, content, status_message

    # --- Execution Methods (Called by ExecutionLayer) ---

    def _read_file(self, file_path: str) -> str:
        """Reads a file and returns its content as observation."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Use max_length to avoid logging massive files
                max_length = 500
                truncated_content = content[:max_length] + ('...' if len(content) > max_length else '')
                self.agent.memory_stream += f"\n[OBSERVATION: READ_FILE] Content of {file_path}:\n---\n{truncated_content}\n---"
                return f"Success: File '{file_path}' read. Content stored in memory."
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found in the current workspace."
        except Exception as e:
            return f"Error reading file '{file_path}': {e}"
            
    def _write_file(self, file_path: str, content: str) -> str:
        """Creates or overwrites a file with the given content."""
        # Safety check for configuration files
        if file_path in ['.env', 'docker-compose.yml', 'Dockerfile']:
            return f"Error: Writing to critical configuration file '{file_path}' is disabled for safety."
            
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            with open(file_path, 'w') as f:
                f.write(content)
                self.agent.memory_stream += f"\n[ACTION SUCCESS] File '{file_path}' written/modified successfully."
                return f"Success: File '{file_path}' written/modified."
        except Exception as e:
            return f"Error writing file '{file_path}': {e}"
            
    def _run_command(self, command: str) -> str:
        """Executes a shell command and captures output."""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                text=True, 
                capture_output=True,
                timeout=10
            )
            
            output = result.stdout.strip()
            max_length = 500
            truncated_output = output[:max_length] + ('...' if len(output) > max_length else '')
            
            self.agent.memory_stream += f"\n[OBSERVATION: RUN_COMMAND] Command: '{command}'. Output:\n---\n{truncated_output}\n---"
            return f"Success: Command executed. Output stored in memory. Stderr: {result.stderr.strip()}"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Error: Command failed with exit code {e.returncode}. Stderr: {e.stderr.strip()}"
            self.agent.memory_stream += f"\n[ACTION FAILURE: RUN_COMMAND] {error_msg}"
            return error_msg
        except subprocess.TimeoutExpired:
            error_msg = f"Error: Command timed out after 10 seconds."
            self.agent.memory_stream += f"\n[ACTION FAILURE: RUN_COMMAND] {error_msg}"
            return error_msg
        except Exception as e:
            error_msg = f"Error: Unknown execution error: {e}"
            self.agent.memory_stream += f"\n[ACTION FAILURE: RUN_COMMAND] {error_msg}"
            return error_msg