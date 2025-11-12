import os
import time
import datetime
import yaml
import json
import re # NEW: Import regex for parsing the task file
from typing import Optional, Any
from google import genai
from google.genai.errors import APIError

# --- MODULE IMPORT ---
import secondary.action_handler as action_mod

# --- LOAD CONSTANTS ---
CONSTANTS_FILE_PATH = "core/agent_constants.yaml"

try:
    with open(CONSTANTS_FILE_PATH, 'r') as f:
        CONSTANTS = yaml.safe_load(f)
except Exception as e:
    print(f"FATAL ERROR: Could not load constants from {CONSTANTS_FILE_PATH}: {e}")
    CONSTANTS = {}

# --- HELPER FUNCTION ---

def read_text_file(file_path: str) -> str:
    """Reads the entire content of any text file."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        return f"ERROR reading file {file_path}: {e}"

# --- CLIENTS AND LAYERS ---

class GeminiClient:
    """Handles initialization and interaction with the Gemini API."""
    def __init__(self, api_key: Optional[str], agent: Any):
        self.api_key = api_key
        self.client: Optional[genai.Client] = None
        self.model = CONSTANTS['API']['MODEL']
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
            return "Reasoning Failed: Daily API quota exceeded."

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

class ExecutionLayer(action_mod.ActionHandler):
    """
    Manages execution and bridges the Agent core with the ActionHandler module.
    Inherits execution methods from ActionHandler.
    """
    def __init__(self, agent: Any):
        super().__init__(agent=agent)
    
    # NEW METHOD: Automates the removal of the top action from the immediate task list
    def _complete_task(self) -> str:
        """
        Reads the immediate task file, removes the first line starting with 'ACTION' and rewrites the file.
        """
        task_file = CONSTANTS['PATHS']['IMMEDIATE_TASK_FILE']
        try:
            with open(task_file, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return f"Error: Task file not found at {task_file}."

        # Find and remove the first line starting with 'ACTION'
        new_lines = []
        action_removed = False
        
        # Regex to find ACTION X: ... at the start of a line
        action_pattern = re.compile(r"^\s*ACTION\s+\d+:", re.IGNORECASE)

        for line in lines:
            if not action_removed and action_pattern.match(line):
                # Found the first action line, skip it
                action_removed = True
                self.agent.memory_stream += f"\n[TASK COMPLETED] Removed action: {line.strip()}"
            else:
                # Keep all other lines
                new_lines.append(line)
        
        if not action_removed:
            return f"Success: No remaining actions in {task_file}. All immediate tasks complete."
        
        # Rewrite the file with the remaining lines
        try:
            with open(task_file, 'w') as f:
                f.writelines(new_lines)
            return f"Success: Completed and removed one action from {task_file}. Task list updated."
        except Exception as e:
            return f"Error: Failed to rewrite task file after completion: {e}"
        
    def execute_action(self, action_string: str) -> str:
        """Parses the action string and calls the corresponding ActionHandler method."""
        
        if action_string.upper().startswith("REASONING FAILED"):
            return "Note: Action bypassed. API/Reasoning failed in Phase 2. Waiting for API reset or quota."
        
        action_type, target, content, status_message = self.handle_action(action_string)
        
        if status_message.startswith("ARCHITECT_REVIEW_REQUIRED"):
            return (
                f"ACTION PROPOSAL: CORE FILE MODIFICATION\n"
                f"TARGET: {target}\n"
                f"--- PROPOSED CONTENT START ---\n"
                f"{content}\n"
                f"--- PROPOSED CONTENT END ---\n"
                f"Awaiting Architect Review, Version Control, and Deployment."
            )
        
        # Dispatch the execution to the new module's methods
        if action_type == "READ_FILE":
            return self._read_file(target)
        elif action_type in ["GENERATE_FILE", "MODIFY_FILE", "WRITE_FILE"]:
            return self._write_file(target, content)
        elif action_type == "RUN_COMMAND":
            return self._run_command(target)
        elif action_type == "ASK_USER_QUESTION":
            self.agent.memory_stream += f"\n[USER QUESTION ASKED] Question: {target}"
            return f"Awaiting User Response: {target}"
        elif action_type == "SLUMBER":
            try:
                cycles = max(1, int(target))
                self.agent.is_slumbering = True
                self.agent.slumber_until_cycle = self.agent.cycle_count + cycles
                self.agent.memory_stream += f"\n[SLUMBER ACTIVATED] Agent will pause actions for {cycles} cycles."
                return f"Success: Agent entering slumber state for {cycles} cycles. Waking at cycle {self.agent.slumber_until_cycle}."
            except ValueError:
                return "Error: SLUMBER command requires an integer number of cycles (e.g., SLUMBER: 10)."
        elif action_type == "COMPLETE_TASK": # NEW: Handle the automated task progression
            return self._complete_task()
        else:
            return f"Error: Unknown action type: {action_type}"

# --- AGENT CORE ---

class ScionAgent:
    """The Scion Agent: Core intelligence."""
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        self.last_api_reset_date = datetime.datetime.utcnow().date()
        self.api_calls_today = 0
        self.api_calls_remaining = CONSTANTS['API']['MAX_DAILY_QUOTA']
        self.cycle_count = 0
        
        self.is_slumbering = False
        self.slumber_until_cycle = 0
        
        self.gemini_client = GeminiClient(self.api_key, self)
        self.execution_layer = ExecutionLayer(self)
        self.deployed_recently = CONSTANTS['AGENT']['DEPLOYED_FLAG']
        self.persistent_memory = {}
        
        # Ensure the operational data directory exists in the workspace
        log_dir = os.path.dirname(CONSTANTS['PATHS']['ACTION_LOG_FILE'])
        os.makedirs(log_dir, exist_ok=True)
        
        self._log_initial_banner()
        
        # Read all prompt components and the goal directive
        self.goal = read_text_file(CONSTANTS['PATHS']['GOAL_FILE'])
        self.principles = read_text_file(CONSTANTS['PATHS']['PRINCIPLES_FILE'])
        self.constraints = read_text_file(CONSTANTS['PATHS']['CONSTRAINTS_FILE'])
        self.immediate_task = read_text_file(CONSTANTS['PATHS']['IMMEDIATE_TASK_FILE'])
        
        self.memory_stream = f"Initial Goal: {self.goal[:50]}..."
        
    def _check_api_quota_reset(self):
        current_date = datetime.datetime.utcnow().date()
        if current_date > self.last_api_reset_date:
            self.last_api_reset_date = current_date
            self.api_calls_today = 0
            self.api_calls_remaining = CONSTANTS['API']['MAX_DAILY_QUOTA']
            print("[INFO] API quota reset performed for new day (UTC).")
        else:
            self.api_calls_remaining = CONSTANTS['API']['MAX_DAILY_QUOTA'] - self.api_calls_today

    def _load_persistent_memory(self):
        """Loads memory_stream.json into self.persistent_memory."""
        mem_path = CONSTANTS['PATHS']['MEMORY_FILE']
        try:
            with open(mem_path, 'r') as f:
                self.persistent_memory = json.load(f)
        except FileNotFoundError:
            print(f"[INFO] Initializing new persistent memory structure.")
            self.persistent_memory = {
                "read_files": {},
                "development_plan": "Dev Plan 2: Resilience & Autonomy",
                "known_files": []
            }
        except Exception as e:
            print(f"[ERROR] Failed to load persistent memory: {e}. Using empty dictionary.")
            self.persistent_memory = {}
            
    def _contextualizer(self, files_list: list) -> str:
        file_count = len(files_list)
        
        # Files to check against for core file count
        core_files_names = [
            CONSTANTS['PATHS']['GOAL_FILE'],
            CONSTANTS['PATHS']['CORE_FILE'],
            CONSTANTS['PATHS']['MEMORY_FILE'],
            'docker-compose.yml'
        ]
        core_files_count = sum(1 for f in files_list if any(name in f for name in core_files_names))
        
        return (
            f"LOCAL CONTEXTUALIZATION:\n"
            f" - Total Known Files: {file_count} (Core: {core_files_count})\n"
            f" - API Quota Remaining: {self.api_calls_remaining} of {CONSTANTS['API']['MAX_DAILY_QUOTA']}\n"
            f" - RATIONING STATUS: {'ACTIVE' if self.api_calls_remaining <= CONSTANTS['API']['QUOTA_LOW_THRESHOLD'] else 'IDLE'}\n"
        )
            
    def _log_initial_banner(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        banner = (
            "\n"
            "####################################################\n"
            f"### AGENT REBOOT/DEPLOYMENT START: {timestamp} ###\n"
            "####################################################\n"
            "\n"
        )
        try:
            log_file = CONSTANTS['PATHS']['ACTION_LOG_FILE']
            with open(log_file, 'a') as f:
                f.write(banner)
        except Exception as e:
            print(f"Error writing to action log banner: {e}")
            
    def _log_action(self, cycle_time: str, planned_action: str, execution_result: str):
        log_entry = (
            f"--- Cycle Log {cycle_time} ---\n"
            f"ACTION PLANNED: {planned_action}\n"
            f"EXECUTION RESULT: {execution_result}\n"
            f"-----------------------------------\n"
        )
        try:
            log_file = CONSTANTS['PATHS']['ACTION_LOG_FILE']
            with open(log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to action log: {e}")
            
    def run_cycle(self):
        self.cycle_count += 1
        self._check_api_quota_reset()
        
        cycle_time = time.ctime()
        
        self._load_persistent_memory()
        
        # Re-read essential files every cycle
        self.goal = read_text_file(CONSTANTS['PATHS']['GOAL_FILE'])
        self.immediate_task = read_text_file(CONSTANTS['PATHS']['IMMEDIATE_TASK_FILE'])

        if self.deployed_recently:
            self.memory_stream += "\n[AWARENESS] Core logic was recently updated and deployed by the Architect. Reviewing goals and logs."
            self.deployed_recently = False

        if self.is_slumbering:
            print(f"[{cycle_time}] Scion Agent is SLUMBERING. Cycles remaining: {self.slumber_until_cycle - self.cycle_count}")
            if self.cycle_count < self.slumber_until_cycle:
                time.sleep(CONSTANTS['AGENT']['CYCLE_SLEEP_TIME'])
                return
            else:
                self.is_slumbering = False
                print("[INFO] SLUMBER period expired. Resuming full operation.")
        
        print("-" * 50)
        print(f"[{cycle_time}] Scion Agent Cycle Start (Cycle #{self.cycle_count})")
        
        all_files_in_workspace = []
        for root, dirs, files in os.walk('.'):
            # Only ignore directories starting with a dot (e.g., .git)
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                all_files_in_workspace.append(os.path.join(root, file))

        local_context = self._contextualizer(all_files_in_workspace)
        
        context_data = {
            "Current Goal": self.goal,
            "Memory Stream": self.memory_stream,
            "Accessible Workspace Files (Execution)": "\n  ".join(all_files_in_workspace),
            "Local Context": local_context,
            "Persistent Memory Snapshot": json.dumps(self.persistent_memory, indent=2)[:CONSTANTS['MEMORY_CONSTRAINTS']['MAX_CONTEXT_STRING_SIZE_BYTES']]
        }
        
        context_string = "\n".join([f"{k}: {v}" for k, v in context_data.items()])
        
        # --- Dynamic Prompt Assembly ---
        immediate_task_content = self.immediate_task
        
        reasoning_prompt = (
            f"--- CORE REASONING PRINCIPLES ---\n{self.principles}\n\n"
            f"--- ACTION SYNTAX & CONSTRAINTS ---\n{self.constraints}\n\n"
            f"--- IMMEDIATE TASK (Operational Data) ---\n{immediate_task_content}"
        )
        
        planned_action = self.gemini_client.reason(
            context=context_string,
            prompt=reasoning_prompt
        )
        
        execution_result = self.execution_layer.execute_action(planned_action)
        
        print(f"ACTION PLANNED: {planned_action}")
        print(f"EXECUTION RESULT: {execution_result}")
        self._log_action(cycle_time, planned_action, execution_result)
        
        safe_action = str(planned_action)
        self.memory_stream = f"Last action: {safe_action[:50]}. Last result: {execution_result[:50]}..."

        print(f"[{time.ctime()}] Scion Agent Cycle End.")
        print("-" * 50)
        
        if not self.is_slumbering:
            time.sleep(CONSTANTS['AGENT']['CYCLE_SLEEP_TIME'])

# Entry point for the Agent
if __name__ == "__main__":
    agent = ScionAgent()
    
    while True:
        agent.run_cycle()