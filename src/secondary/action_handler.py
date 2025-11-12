# src/secondary/action_handler.py

import os
import subprocess
import json
import time
from typing import Tuple, Optional, Any
from core.utilities import read_text_file, write_text_file # Ensure write_text_file is imported

class ActionHandler:
    """
    Handles the execution of agent actions (READ_FILE, WRITE_FILE, RUN_COMMAND, etc.)
    and updates the agent's internal state (memory_stream, file content cache).
    """

    def __init__(self, agent: Any):
        self.agent = agent
        self.constants = self.agent.constants
        self.max_log_size = self.constants['MEMORY_CONSTRAINTS']['MAX_LOG_FILE_SIZE_BYTES']

    def handle_action(self, action_string: str) -> Tuple[str, str, str, str]:
        """Parses a single action string into its components."""
        parts = action_string.strip().split(':', 1)
        action_type = parts[0].strip().upper()
        target = parts[1].split('\n', 1)[0].strip() if len(parts) > 1 else ""
        content = parts[1].split('\n', 1)[1].strip() if len(parts) > 1 and '\n' in parts[1] else ""
        
        # Special check for core file modification (Architect Review)
        if target.startswith("core/") and action_type in ["WRITE_FILE", "MODIFY_FILE", "GENERATE_FILE"]:
             return action_type, target, content, "ARCHITECT_REVIEW_REQUIRED"
             
        return action_type, target, content, "ACTION_READY"

    # --- Core Execution Methods ---
    
    def _read_file(self, file_path: str) -> str:
        """Reads a file and stores its content in the agent's memory cache."""
        try:
            # Check the cache first
            if file_path in self.agent.known_file_contents:
                return f"Success: File '{file_path}' already in memory cache. Content is available to Gemini."
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Store content in the dedicated dictionary
            self.agent.known_file_contents[file_path] = content 

            truncated_content = content[:100] + '...' if len(content) > 100 else content
            
            return f"Success: File '{file_path}' read. Content stored in memory cache. Truncated content: '{truncated_content}'"
        
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found in the current workspace."
        except Exception as e:
            return f"Error: Failed to read file '{file_path}': {e}"

    def _write_file(self, file_path: str, content: str) -> str:
        """Writes content to a file."""
        try:
            write_text_file(file_path, content)
            
            # Invalidate the cache if the file was written/modified
            if file_path in self.agent.known_file_contents:
                 del self.agent.known_file_contents[file_path]

            return f"Success: File '{file_path}' written/modified."
        except Exception as e:
            return f"Error: Failed to write file '{file_path}': {e}"

    def _run_command(self, command: str) -> str:
        """Runs a shell command and captures output into the memory stream."""
        try:
            # Execute command with a timeout
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10, 
                check=True
            )
            
            output = result.stdout.strip()
            # Append command and output to the agent's memory stream
            self.agent.memory_stream += f"\n[RUN_COMMAND] Command: '{command}'. Output:\n---\n{output}\n---"
            
            # Truncated output for the final result message
            truncated_output = output[:100] + '...' if len(output) > 100 else output
            return f"Success: Command executed. Output stored in memory. Truncated Output: '{truncated_output}'"
            
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
            
    def _create_debug_snapshot(self) -> str:
        """
        Gathers key operational data files and recent logs, and saves it to a file
        for easy user access.
        """
        SNAPSHOT_FILE = "data/debug_snapshot.txt"
        snapshot_content = []

        # 1. Action Queue
        queue = self.agent.task_manager.load_queue()
        snapshot_content.append(f"--- DATA/ACTION_QUEUE.JSON ---\n{json.dumps(queue, indent=2)}")

        # 2. Persistent Memory Stream
        mem = self.agent.memory_manager.load()
        snapshot_content.append(f"--- DATA/MEMORY_STREAM.JSON (Persistent Memory) ---\n{json.dumps(mem, indent=2)}")
        
        # 3. Agent's in-cycle memory stream
        snapshot_content.append(f"--- AGENT CORE MEMORY STREAM (Context History) ---\n{self.agent.memory_stream}")

        # 4. Last 100 lines of Action Log
        try:
            log_file_path = self.constants['PATHS']['ACTION_LOG_FILE']
            with open(log_file_path, 'r') as f:
                log_lines = f.readlines()
                log_snippet = "".join(log_lines[-100:])
                snapshot_content.append(f"--- DATA/ACTION_LOG.TXT (Last 100 Lines) ---\n{log_snippet}")
        except Exception as e:
             snapshot_content.append(f"--- DATA/ACTION_LOG.TXT ---\nError reading log file: {e}")

        final_snapshot = "\n\n".join(snapshot_content)
        
        # Write to file
        try:
            write_text_file(SNAPSHOT_FILE, final_snapshot)
            self.agent.memory_stream += f"\n[DEBUG_SNAPSHOT_CREATED] Full snapshot created and saved to {SNAPSHOT_FILE}."
            return f"Success: Debug snapshot created and saved to '{SNAPSHOT_FILE}'. Please retrieve this file to provide full context."
        except Exception as e:
            error_msg = f"Error: Failed to write debug snapshot to {SNAPSHOT_FILE}: {e}"
            self.agent.memory_stream += f"\n[DEBUG_SNAPSHOT_FAILURE] {error_msg}"
            return error_msg