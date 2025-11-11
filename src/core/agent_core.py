import os
import time
import re
import subprocess
import datetime
from typing import Optional, Any
from google import genai
from google.genai.errors import APIError 

# --- CONFIGURATION ---
ACTION_LOG_FILE = "action_log.txt" # Written to /app/workspace
API_MAX_DAILY_QUOTA = 100
API_QUOTA_LOW_THRESHOLD = 10
CYCLE_SLEEP_TIME = 5 # Seconds per cycle (Base for SLUMBER)
# --- FILE PATHS (All files are accessed relative to the Agent's CWD: /app/workspace) ---
GOAL_FILE_PATH = "goal.txt" 
CORE_FILE_PATH = "core/agent_core.py"
# ---------------------

# --- Function to read and parse the goal file ---
def read_goal_directive(file_path: str) -> str:
    """Reads the entire content of the goal file, which is now in /app/workspace."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return f"ERROR: Goal file '{file_path}' not found. Set a new long-term goal (LTG)."
    except Exception as e:
        return f"ERROR reading goal file: {e}"
# -----------------------------------------------------

# (GeminiClient class remains unchanged)
class GeminiClient:
    """Handles initialization and interaction with the Gemini API."""
    # (Implementation omitted for brevity, it is unchanged)
    def __init__(self, api_key: Optional[str], agent: Any):
        self.api_key = api_key
        self.client: Optional[genai.Client] = None
        self.model = 'gemini-2.5-flash'
        self.agent = agent
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Client Error] Initialization failed: {e}")
                self.client = None

    def reason(self, context: str, prompt: str) -> str:
        """Calls the Gemini API to get a reasoned action or step."""
        if not self.client:
            return "Reasoning Failed: Client not initialized due to missing API Key or error."
            
        if self.agent.api_calls_remaining <= 0:
            return "Reasoning Failed: Daily API quota exceeded. Must wait until midnight UTC."

        full_prompt = f"CONTEXT:\n{context}\n\nTASK:\n{prompt}"
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[full_prompt]
            )
            
            self.agent.api_calls_today += 1 
            
            if not response.candidates:
                prompt_feedback = response.prompt_feedback 
                return f"REASONING FAILED (BLOCKED): {prompt_feedback.block_reason.name if prompt_feedback and prompt_feedback.block_reason else 'N/A'}"
            
            return response.text.strip() if response.text else "REASONING FAILED (EMPTY CANDIDATE)"
            
        except APIError as e:
            self.agent.api_calls_today += 1
            return f"REASONING FAILED (API): {e}"
        except Exception as e:
            return f"REASONING FAILED (UNKNOWN): {e}"


# --- Action Handler Class for Execution (PATH ADJUSTED) ---
class ActionHandler:
    """Parses and executes the actions determined by the LLM."""
    
    def __init__(self, agent: Any):
        self.agent = agent
        self.action_pattern = re.compile(r"(\w+):\s*(.*?)(?:\n|$)", re.DOTALL)
        
    def execute_action(self, action_string: str) -> str:
        """Parses the action string and calls the corresponding method."""
        
        match = self.action_pattern.match(action_string.strip())
        
        if not match:
            if "Reasoning Failed" in action_string:
                return "Note: Action bypassed. API/Reasoning failed in Phase 2. Waiting for API reset."
            return f"Error: Action format not recognized: {action_string}"
            
        action_type = match.group(1).upper()
        content = match.group(2).strip()
        
        # Dispatch the action
        if action_type == "READ_FILE":
            return self._read_file(content)
        elif action_type in ["GENERATE_FILE", "MODIFY_FILE", "WRITE_FILE"]:
            parts = content.split('\n', 1)
            file_path = parts[0].strip()
            file_content = parts[1].strip() if len(parts) > 1 else ""
            
            # --- CRITICAL: ARCHITECTURAL REVIEW PROTOCOL HOOK ---
            # Checks for files that originated in the src directory
            if file_path in [self.agent.goal_file_path, CORE_FILE_PATH] or file_path.startswith('secondary/'):
                # Note: The agent is reading the modified file from /app/workspace 
                # but the proposal targets the corresponding path in the source of truth
                return (
                    f"ACTION PROPOSAL: CORE FILE MODIFICATION\n"
                    f"TARGET: {file_path}\n"
                    f"--- PROPOSED CONTENT START ---\n"
                    f"{file_content}\n"
                    f"--- PROPOSED CONTENT END ---\n"
                    f"Awaiting Architect Review, Version Control, and Deployment."
                )
            # ------------------------------------------------------
            
            return self._write_file(file_path, file_content)
        elif action_type == "RUN_COMMAND":
            return self._run_command(content)
        elif action_type == "ASK_USER_QUESTION":
            self.agent.memory_stream += f"\n[USER QUESTION ASKED] Question: {content}"
            return f"Awaiting User Response: {content}"
        elif action_type == "SLUMBER":
            try:
                cycles = max(1, int(content))
                slumber_time = cycles * CYCLE_SLEEP_TIME
                self.agent.is_slumbering = True
                self.agent.slumber_until_cycle = self.agent.cycle_count + cycles
                self.agent.memory_stream += f"\n[SLUMBER ACTIVATED] Agent will pause actions for {cycles} cycles ({slumber_time} seconds)."
                return f"Success: Agent entering slumber state for {cycles} cycles. Waking at cycle {self.agent.slumber_until_cycle}."
            except ValueError:
                return "Error: SLUMBER command requires an integer number of cycles (e.g., SLUMBER: 10)."
        else:
            return f"Error: Unknown action type: {action_type}"

    def _read_file(self, file_path: str) -> str:
        """Reads a file and returns its content as observation."""
        # Read is always from CWD (/app/workspace)
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                self.agent.memory_stream += f"\n[OBSERVATION: READ_FILE] Content of {file_path}:\n---\n{content}\n---"
                return f"Success: File '{file_path}' read. Content stored in memory."
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found in the current workspace."
        except Exception as e:
            return f"Error reading file '{file_path}': {e}"
            
    def _write_file(self, file_path: str, content: str) -> str:
        """Creates or overwrites a file with the given content. Writes only occur in /app/workspace."""
        if file_path in ['.env', 'docker-compose.yml', 'Dockerfile']:
            return f"Error: Writing to critical configuration file '{file_path}' is disabled for safety."
            
        try:
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
            truncated_output = output[:500] + ('...' if len(output) > 500 else '')
            
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


# -----------------------------------------------------

class ScionAgent:
    """
    The Scion Agent: Core intelligence, designed for self-evolution and succession.
    """
    def __init__(self, goal_file_path: str):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.goal_file_path = goal_file_path
        
        self.last_api_reset_date = datetime.datetime.utcnow().date()
        self.api_calls_today = 0
        self.api_calls_remaining = API_MAX_DAILY_QUOTA
        self.cycle_count = 0 
        
        self.is_slumbering = False
        self.slumber_until_cycle = 0
        
        self.gemini_client = GeminiClient(self.api_key, self)
        self.action_handler = ActionHandler(self)
        
        self.goal = read_goal_directive(self.goal_file_path) 
        self.memory_stream = f"Initial Goal: {self.goal[:50]}..."
            
    def _check_api_quota_reset(self):
        """Checks if a new day has started (UTC) and resets the quota counters."""
        current_date = datetime.datetime.utcnow().date()
        if current_date > self.last_api_reset_date:
            self.last_api_reset_date = current_date
            self.api_calls_today = 0
            self.api_calls_remaining = API_MAX_DAILY_QUOTA
            print("[INFO] API quota reset performed for new day (UTC).")
        else:
            self.api_calls_remaining = API_MAX_DAILY_QUOTA - self.api_calls_today
            
    def _contextualizer(self, files_list: list) -> str:
        """Local AI Seed: Processes simple data to provide structured context."""
        
        file_count = len(files_list)
        core_files_names = [GOAL_FILE_PATH, CORE_FILE_PATH, 'docker-compose.yml']
        core_files_count = sum(1 for f in files_list if any(name in f for name in core_files_names))
        
        summary = (
            f"LOCAL CONTEXTUALIZATION:\n"
            f" - Total Known Files: {file_count} (Core: {core_files_count})\n"
            f" - API Quota Remaining: {self.api_calls_remaining} of {API_MAX_DAILY_QUOTA}\n"
            f" - RATIONING STATUS: {'ACTIVE' if self.api_calls_remaining <= API_QUOTA_LOW_THRESHOLD else 'IDLE'}\n"
        )
        return summary
            
    def _log_action(self, cycle_time: str, planned_action: str, execution_result: str):
        """Appends the cycle's action and result to a persistent log file (written to /app/workspace)."""
        log_entry = (
            f"--- Cycle Log {cycle_time} ---\n"
            f"ACTION PLANNED: {planned_action}\n"
            f"EXECUTION RESULT: {execution_result}\n"
            f"-----------------------------------\n"
        )
        try:
            with open(ACTION_LOG_FILE, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to action log: {e}")
            
    def run_cycle(self):
        self.cycle_count += 1
        self._check_api_quota_reset()
        
        cycle_time = time.ctime()
        self.goal = read_goal_directive(self.goal_file_path)

        # --- SLUMBER CHECK ---
        if self.is_slumbering:
            print(f"[{cycle_time}] Scion Agent is SLUMBERING. Cycles remaining: {self.slumber_until_cycle - self.cycle_count}")
            if self.cycle_count < self.slumber_until_cycle:
                time.sleep(CYCLE_SLEEP_TIME)
                return 
            else:
                self.is_slumbering = False
                print("[INFO] SLUMBER period expired. Resuming full operation.")
        # ---------------------
        
        # START CYCLE OUTPUT
        print("-" * 50)
        print(f"[{cycle_time}] Scion Agent Cycle Start (Cycle #{self.cycle_count})")
        
        # Phase 1: OBSERVE 
        # Since CWD is /app/workspace, os.listdir('.') shows all files the Agent can access/edit.
        all_files_in_workspace = []
        for root, dirs, files in os.walk('.'):
            # Exclude the hidden .git directory from observation
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                all_files_in_workspace.append(os.path.join(root, file))

        local_context = self._contextualizer(all_files_in_workspace)
        
        context_data = {
            "Current Goal": self.goal,
            "Memory Stream": self.memory_stream,
            "Accessible Workspace Files (Execution)": "\n  ".join(all_files_in_workspace),
            "Local Context": local_context
        }
        context_string = "\n".join([f"{k}: {v}" for k, v in context_data.items()])
        
        # Phase 2: REASON 
        reasoning_prompt = (
            "Based on the CONTEXT, you must now refactor your logic. "
            "You are running from the workspace, which is a copy of source files. "
            "If you modify a source file (goal.txt, core/agent_core.py, or a secondary/ file), "
            "you must use the **Architectural Review Protocol** and the **full path from the workspace (e.g., core/agent_core.py)** as the target. "
            "Your first task is to **create a new file, secondary/action_handler.py**, and propose an update to **core/agent_core.py** to use it."
            "If waiting for the Architect, use 'SLUMBER: [CYCLES]'."
            "Respond ONLY with the single, most optimal action."
        )
        
        planned_action = self.gemini_client.reason(
            context=context_string,
            prompt=reasoning_prompt
        )
        
        # Phase 3: ACT (Execution handled by ActionHandler)
        execution_result = self.action_handler.execute_action(planned_action)
        
        # Log action and result to console and file
        print(f"ACTION PLANNED: {planned_action}")
        print(f"EXECUTION RESULT: {execution_result}")
        self._log_action(cycle_time, planned_action, execution_result)
        
        # Update memory stream 
        safe_action = str(planned_action)
        self.memory_stream = f"Last action: {safe_action[:50]}. Last result: {execution_result[:50]}..."

        print(f"[{time.ctime()}] Scion Agent Cycle End.")
        print("-" * 50)
        
        if not self.is_slumbering:
            time.sleep(CYCLE_SLEEP_TIME)

# Entry point for the Agent
if __name__ == "__main__":
    agent = ScionAgent(GOAL_FILE_PATH)
    
    while True:
        agent.run_cycle()