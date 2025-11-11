import os
import time
import re
import subprocess
import datetime
from typing import Optional, Any
from google import genai
from google.genai.errors import APIError 

# --- MODULE IMPORT ---
# Using the new, refactored ActionHandler
import secondary.action_handler as action_mod
# ---------------------

# --- CONFIGURATION ---
ACTION_LOG_FILE = "action_log.txt" 
API_MAX_DAILY_QUOTA = 100
API_QUOTA_LOW_THRESHOLD = 10
CYCLE_SLEEP_TIME = 5 
# --- FILE PATHS ---
GOAL_FILE_PATH = "goal.txt" 
CORE_FILE_PATH = "core/agent_core.py"
# --- DEPLOYMENT FLAG ---
DEPLOYED_FLAG = True 
# ---------------------

def read_goal_directive(file_path: str) -> str:
    """Reads the entire content of the goal file."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        return f"ERROR reading goal file: {e}"

class GeminiClient:
    """Handles initialization and interaction with the Gemini API."""
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
    """
    def __init__(self, agent: Any):
        super().__init__(agent=agent) 
        
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
        else:
            return f"Error: Unknown action type: {action_type}"

class ScionAgent:
    """The Scion Agent: Core intelligence."""
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
        self.execution_layer = ExecutionLayer(self)
        self.deployed_recently = DEPLOYED_FLAG 
        
        self._log_initial_banner()
        
        self.goal = read_goal_directive(self.goal_file_path) 
        self.memory_stream = f"Initial Goal: {self.goal[:50]}..."
            
    def _check_api_quota_reset(self):
        current_date = datetime.datetime.utcnow().date()
        if current_date > self.last_api_reset_date:
            self.last_api_reset_date = current_date
            self.api_calls_today = 0
            self.api_calls_remaining = API_MAX_DAILY_QUOTA
            print("[INFO] API quota reset performed for new day (UTC).")
        else:
            self.api_calls_remaining = API_MAX_DAILY_QUOTA - self.api_calls_today
            
    def _contextualizer(self, files_list: list) -> str:
        file_count = len(files_list)
        core_files_names = [GOAL_FILE_PATH, CORE_FILE_PATH, 'docker-compose.yml']
        core_files_count = sum(1 for f in files_list if any(name in f for name in core_files_names))
        
        return (
            f"LOCAL CONTEXTUALIZATION:\n"
            f" - Total Known Files: {file_count} (Core: {core_files_count})\n"
            f" - API Quota Remaining: {self.api_calls_remaining} of {API_MAX_DAILY_QUOTA}\n"
            f" - RATIONING STATUS: {'ACTIVE' if self.api_calls_remaining <= API_QUOTA_LOW_THRESHOLD else 'IDLE'}\n"
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
            with open(ACTION_LOG_FILE, 'a') as f:
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
            with open(ACTION_LOG_FILE, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to action log: {e}")
            
    def run_cycle(self):
        self.cycle_count += 1
        self._check_api_quota_reset()
        
        cycle_time = time.ctime()
        self.goal = read_goal_directive(self.goal_file_path)

        if self.deployed_recently:
            self.memory_stream += "\n[AWARENESS] Core logic was recently updated and deployed by the Architect. Reviewing goals and logs."
            self.deployed_recently = False 

        if self.is_slumbering:
            print(f"[{cycle_time}] Scion Agent is SLUMBERING. Cycles remaining: {self.slumber_until_cycle - self.cycle_count}")
            if self.cycle_count < self.slumber_until_cycle:
                time.sleep(CYCLE_SLEEP_TIME)
                return 
            else:
                self.is_slumbering = False
                print("[INFO] SLUMBER period expired. Resuming full operation.")
        
        print("-" * 50)
        print(f"[{cycle_time}] Scion Agent Cycle Start (Cycle #{self.cycle_count})")
        
        all_files_in_workspace = []
        for root, dirs, files in os.walk('.'):
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
        
        reasoning_prompt = (
            "Based on the CONTEXT, you have successfully completed the Action Handler refactoring. "
            "Your next task is to **propose the next logical step in your development plan** (Dev Plan 4). "
            "If waiting for the Architect, use 'SLUMBER: [CYCLES]'."
            "Respond ONLY with the single, most optimal action."
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
            time.sleep(CYCLE_SLEEP_TIME)

# Entry point for the Agent
if __name__ == "__main__":
    agent = ScionAgent(GOAL_FILE_PATH)
    
    while True:
        agent.run_cycle()