import os
import time
import re
import subprocess
import datetime
from typing import Optional, Any
from google import genai
from google.genai.errors import APIError 

# --- CONFIGURATION ---
ACTION_LOG_FILE = "action_log.txt"
API_MAX_DAILY_QUOTA = 100 # Estimated safe limit for free tier
API_QUOTA_LOW_THRESHOLD = 10 # When to start rationing
# ---------------------

# --- Function to read and parse the goal file ---
def read_goal_directive(file_path: str) -> str:
    """Reads the entire content of the goal file."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "ERROR: Goal file not found. Set a new long-term goal (LTG)."
    except Exception as e:
        return f"ERROR reading goal file: {e}"
# -----------------------------------------------------

# --- Gemini Client Utility Class for Reasoning ---
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

# -----------------------------------------------------

# --- Action Handler Class for Execution (UPDATED for Proposal) ---
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
        elif action_type == "GENERATE_FILE" or action_type == "MODIFY_FILE" or action_type == "WRITE_FILE":
            # For writes, the content is split into path and content
            parts = content.split('\n', 1)
            file_path = parts[0].strip()
            file_content = parts[1].strip() if len(parts) > 1 else ""
            
            # --- CRITICAL: ARCHITECTURAL REVIEW PROTOCOL HOOK ---
            if file_path in [self.agent.goal_file_path, 'agent_core.py']:
                # Action is a Core File Modification -> RETURN PROPOSAL
                return (
                    f"ACTION PROPOSAL: CORE FILE MODIFICATION\n"
                    f"TARGET: {file_path}\n"
                    f"--- PROPOSED CONTENT START ---\n"
                    f"{file_content}\n"
                    f"--- PROPOSED CONTENT END ---\n"
                    f"Awaiting Architect Review, Version Control, and Deployment."
                )
            # ------------------------------------------------------
            
            # If not a core file, execute the write immediately
            return self._write_file(file_path, file_content)
        elif action_type == "RUN_COMMAND":
            return self._run_command(content)
        elif action_type == "ASK_USER_QUESTION":
            self.agent.memory_stream += f"\n[USER QUESTION ASKED] Question: {content}"
            return f"Awaiting User Response: {content}"
        else:
            return f"Error: Unknown action type: {action_type}"

    # The rest of the methods (_read_file, _write_file, _run_command) remain the same.
    # The _run_command safety check for "git push" is now irrelevant as the Agent won't be managing its own repo.
    
    def _read_file(self, file_path: str) -> str:
        """Reads a file and returns its content as observation."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                self.agent.memory_stream += f"\n[OBSERVATION: READ_FILE] Content of {file_path}:\n---\n{content}\n---"
                return f"Success: File '{file_path}' read. Content stored in memory."
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found."
        except Exception as e:
            return f"Error reading file '{file_path}': {e}"
            
    def _write_file(self, file_path: str, content: str) -> str:
        """Creates or overwrites a file with the given content. Only called for non-core files."""
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
    It operates on a cycle of observation, reasoning, and action.
    """
    def __init__(self, goal_file_path: str):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.goal_file_path = goal_file_path
        
        self.last_api_reset_date = datetime.datetime.utcnow().date()
        self.api_calls_today = 0
        self.api_calls_remaining = API_MAX_DAILY_QUOTA
        
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
        core_files_count = sum(1 for f in files_list if f in [self.goal_file_path, 'agent_core.py', 'docker-compose.yml'])
        
        summary = (
            f"LOCAL CONTEXTUALIZATION:\n"
            f" - Files in CWD: {file_count} (Core: {core_files_count})\n"
            f" - API Quota Remaining: {self.api_calls_remaining} of {API_MAX_DAILY_QUOTA}\n"
            f" - RATIONING STATUS: {'ACTIVE' if self.api_calls_remaining <= API_QUOTA_LOW_THRESHOLD else 'IDLE'}\n"
        )
        return summary
            
    def _log_action(self, cycle_time: str, planned_action: str, execution_result: str):
        """Appends the cycle's action and result to a persistent log file."""
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
        """
        The main loop for the Scion Agent's operation.
        Phase 1: Observe (Read environment, goals, memory)
        Phase 2: Reason (Use LLM to plan the next step)
        Phase 3: Act (Execute the planned step)
        """
        self._check_api_quota_reset()
        
        cycle_time = time.ctime()
        self.goal = read_goal_directive(self.goal_file_path)

        # START CYCLE OUTPUT
        print("-" * 50)
        print(f"[{cycle_time}] Scion Agent Cycle Start")
        
        # Phase 1: OBSERVE (Collect Data for Reasoning)
        files_list = os.listdir('.')
        local_context = self._contextualizer(files_list)
        
        context_data = {
            "Current Goal": self.goal,
            "Memory Stream": self.memory_stream,
            "Working Directory Files": "\n  ".join(files_list),
            "Local Context": local_context
        }
        context_string = "\n".join([f"{k}: {v}" for k, v in context_data.items()])
        
        # Phase 2: REASON 
        reasoning_prompt = (
            "Based on the CONTEXT, especially the 'Local Contextualization' and 'API Quota Remaining', "
            "determine the single, most optimal action. If API Quota is LOW, prioritize 'ASK_USER_QUESTION: Is this next step worth one of my last API calls?' "
            "Follow the ARCHITECTURAL REVIEW PROTOCOL for core files. "
            "Respond ONLY with the action. (e.g., 'READ_FILE: target.txt', 'WRITE_FILE: next_file.txt\\nContent goes here', 'RUN_COMMAND: git status', 'ASK_USER_QUESTION: ...')"
        )
        
        planned_action = self.gemini_client.reason(
            context=context_string,
            prompt=reasoning_prompt
        )
        
        # Phase 3: ACT (Execute the planned action)
        
        # --- ARCHITECTURAL REVIEW LAYER ---
        # The ActionHandler handles the interception and proposal generation.
        execution_result = self.action_handler.execute_action(planned_action)
        # -----------------------------------
        
        # Log action and result to console and file
        print(f"ACTION PLANNED: {planned_action}")
        print(f"EXECUTION RESULT: {execution_result}")
        self._log_action(cycle_time, planned_action, execution_result)
        
        # Update memory stream 
        safe_action = str(planned_action)
        self.memory_stream = f"Last action: {safe_action[:50]}. Last result: {execution_result[:50]}..."

        print(f"[{time.ctime()}] Scion Agent Cycle End.")
        print("-" * 50)
        time.sleep(5) # Delay the next cycle

# Entry point for the Agent
if __name__ == "__main__":
    goal_file = "goal.txt"
    agent = ScionAgent(goal_file)
    
    # The Agent's main loop
    while True:
        agent.run_cycle()