# src/core/agent_core.py

import os
import time
import datetime
import yaml
import json
from typing import Optional, Any, Dict
from google import genai
from google.genai.errors import APIError

# --- MODULE IMPORTS ---
import secondary.action_handler as action_mod
# Import new core modules
from core.utilities import read_text_file, log_action, log_initial_banner, contextualize_filesystem
from core.memory_manager import MemoryManager
from core.resource_manager import ResourceManager
from core.task_manager import TaskManager
from core.models import ACTION_QUEUE_SCHEMA # Import the schema from the new models.py

# --- LOAD CONSTANTS ---
CONSTANTS_FILE_PATH = "core/agent_constants.yaml"

try:
    with open(CONSTANTS_FILE_PATH, 'r') as f:
        CONSTANTS = yaml.safe_load(f)
except Exception as e:
    print(f"FATAL ERROR: Could not load constants from {CONSTANTS_FILE_PATH}: {e}")
    CONSTANTS = {}

# --- CLIENTS AND LAYERS ---

class GeminiClient:
    """Handles initialization and interaction with the Gemini API."""
    def __init__(self, api_key: Optional[str], resource_manager: ResourceManager):
        self.api_key = api_key
        self.client: Optional[genai.Client] = None
        self.model = CONSTANTS['API']['MODEL']
        self.resources = resource_manager
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Client Error] Initialization failed: {e}")
                self.client = None

    def reason(self, context: str, prompt: str, schema: Optional[Any] = None) -> str:
        """Calls the Gemini API to get a reasoned action or step, supporting JSON mode."""
        if not self.client:
            return "Reasoning Failed: Client not initialized due to missing API Key or error."
            
        if self.resources.api_calls_remaining <= 0:
            return "Reasoning Failed: Daily API quota exceeded."

        full_prompt = f"CONTEXT:\n{context}\n\nTASK:\n{prompt}"
        
        config = None
        if schema:
            config = genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema
            )
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[full_prompt],
                config=config
            )
            self.resources.api_calls_today += 1
            
            if not response.candidates:
                prompt_feedback = response.prompt_feedback
                return f"REASONING FAILED (BLOCKED): {prompt_feedback.block_reason.name if prompt_feedback and prompt_feedback.block_reason else 'N/A'}"
            
            return response.text.strip() if response.text else "REASONING FAILED (EMPTY CANDIDATE)"
            
        except APIError as e:
            self.resources.api_calls_today += 1
            return f"REASONING FAILED (API): {e}"
        except Exception as e:
            return f"REASONING FAILED (UNKNOWN): {e}"

class ExecutionLayer(action_mod.ActionHandler):
    """
    Manages execution and bridges the Agent core with the ActionHandler module.
    Inherits execution methods from ActionHandler.
    """
    def __init__(self, agent: Any, task_manager: TaskManager):
        super().__init__(agent=agent)
        self.task_manager = task_manager
        
    def execute_action(self, action_string: str) -> str:
        """Parses the action string and calls the corresponding ActionHandler method."""
        
        if action_string.upper().startswith("REASONING FAILED"):
            return "Note: Action bypassed. API/Reasoning failed in Phase 2. Waiting for API reset or quota."
        
        # NOTE: The action_string here is guaranteed to be a single, executable action (e.g., READ_FILE: path)
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
            # NOTE: When the LLM decides to change a file that was previously read, it should
            # ensure the file is removed from known_file_contents to force a fresh read later.
            if target in self.agent.known_file_contents:
                 del self.agent.known_file_contents[target]
            return self._write_file(target, content)
        elif action_type == "RUN_COMMAND":
            return self._run_command(target)
        elif action_type == "SLUMBER":
            try:
                cycles = max(1, int(target))
                self.agent.resources.is_slumbering = True
                self.agent.resources.slumber_until_cycle = self.agent.resources.cycle_count + cycles
                self.agent.memory_stream += f"\n[SLUMBER ACTIVATED] Agent will pause actions for {cycles} cycles."
                return f"Success: Agent entering slumber state for {cycles} cycles. Waking at cycle {self.agent.resources.slumber_until_cycle}."
            except ValueError:
                return "Error: SLUMBER command requires an integer number of cycles (e.g., SLUMBER: 10)."
        elif action_type == "NEXT_TASK": # Triggers the start of a new, high-level task
            # target contains the new high-level task directive
            result, self.agent.memory_stream = self.task_manager.handle_next_task(self.agent.memory_stream, target)
            return result
        elif action_type == "CREATE_DEBUG_SNAPSHOT":
            # New custom action for the user's debugging request
            return self._create_debug_snapshot()
        else:
            return f"Error: Unknown action type: {action_type}"

# --- AGENT CORE ---

class ScionAgent:
    """The Scion Agent: Core intelligence and orchestrator."""
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.constants = CONSTANTS
        
        # Initialize sub-managers
        self.resources = ResourceManager(self.constants)
        self.memory_manager = MemoryManager(self.constants)
        self.task_manager = TaskManager(self.constants)

        self.deployed_recently = self.constants['AGENT']['DEPLOYED_FLAG']
        self.persistent_memory = self.memory_manager.load() # Load memory on initialization
        
        # --- NEW DEDICATED MEMORY FOR READ FILE CONTENTS ---
        self.known_file_contents: Dict[str, str] = {}
        # --------------------------------------------------
        
        # Initialize Layers
        self.gemini_client = GeminiClient(self.api_key, self.resources)
        self.execution_layer = ExecutionLayer(self, self.task_manager)
        
        # Ensure the operational data directory exists in the workspace
        log_dir = os.path.dirname(self.constants['PATHS']['ACTION_LOG_FILE'])
        os.makedirs(log_dir, exist_ok=True)
        
        log_initial_banner(self.constants)
        
        # Read all prompt components and the goal directive
        self.goal = read_text_file(self.constants['PATHS']['GOAL_FILE'])
        self.principles = read_text_file(self.constants['PATHS']['PRINCIPLES_FILE'])
        # Read action syntax from its new dedicated file
        self.action_syntax = read_text_file(self.constants['PATHS']['ACTION_SYNTAX_FILE'])
        self.immediate_task_human = read_text_file(self.constants['PATHS']['IMMEDIATE_TASK_FILE'])
        
        self.memory_stream = f"Initial Goal: {self.goal[:50]}..."
        
    def run_cycle(self):
        self.resources.cycle_count += 1
        self.resources.check_api_quota_reset()
        
        cycle_time = time.ctime()
        
        # Handle slumber
        if self.resources.handle_slumber():
            return
            
        print("-" * 50)
        print(f"[{cycle_time}] Scion Agent Cycle Start (Cycle #{self.resources.cycle_count})")
        
        # Re-read essential files every cycle (Task/Goal/Memory can be modified by agent or human)
        self.goal = read_text_file(self.constants['PATHS']['GOAL_FILE'])
        self.immediate_task_human = read_text_file(self.constants['PATHS']['IMMEDIATE_TASK_FILE'])
        self.persistent_memory = self.memory_manager.load()

        # --- 1. Get Next Action from Task Manager ---
        planned_action, action_source = self.task_manager.get_next_action()
        
        # --- 2. Execution / Decomposition Decision ---
        
        if action_source == "QUEUE_ACTION":
            final_action = planned_action
            print(f"Action source: QUEUE_ACTION. Executing action: {final_action[:50]}...")
            
        elif action_source == "DECOMPOSITION_NEEDED":
            # --- 2a. Dynamic Prompt Assembly (for Decomposition) ---
            print("Action source: DECOMPOSITION_NEEDED. Calling LLM for action queue.")
            reasoning_prompt = (
                f"The action queue is EMPTY. Your immediate task is: '{planned_action}'.\n"
                f"Based on your principles and constraints, decompose this human task into a list of machine-readable actions.\n"
                f"CRITICAL CONSTRAINT: All file paths you use for READ_FILE, WRITE_FILE, GENERATE_FILE, or MODIFY_FILE MUST be relative to the workspace root (e.g., 'src/core/agent_core.py', NOT 'agent_core.py'). If reading/editing, the file MUST exist in the provided 'Current Workspace File Structure'. If creating a new file, the path MUST NOT exist.\n\n"
                f"{self.action_syntax}"
            )
            
            # --- 3. Build Context ---
            
            all_files_in_workspace = []
            for root, dirs, files in os.walk('.'):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for file in files:
                    relative_path = os.path.join(root, file).lstrip('./')
                    all_files_in_workspace.append(relative_path)

            file_structure_string = "\n".join(all_files_in_workspace)
            
            # Convert known_file_contents dict to a context string for Gemini
            known_file_contents_string = "\n\n".join(
                [f"--- FILE CONTENTS: {path} ---\n{content}" for path, content in self.known_file_contents.items()]
            )

            # Limit the total context size
            max_context = self.constants['MEMORY_CONSTRAINTS']['MAX_CONTEXT_STRING_SIZE_BYTES']
            
            context_data = {
                "Current Goal": self.goal,
                "Memory Stream (Last Action/Result)": self.memory_stream,
                "Current Workspace File Structure": file_structure_string,
                "Persistent Memory Snapshot": json.dumps(self.persistent_memory, indent=2)[:max_context],
                "RECENTLY READ FILE CONTENTS (DO NOT READ AGAIN)": known_file_contents_string[:max_context] # Include the full contents
            }
            
            context_string = "\n".join([f"{k}:\n{v}" for k, v in context_data.items()])
            
            # --- 4. Reasoning/Execution (JSON MODE LOGIC) ---
            
            queue_content_json_str = self.gemini_client.reason(
                context=context_string,
                prompt=reasoning_prompt,
                schema=ACTION_QUEUE_SCHEMA
            )
            
            if queue_content_json_str.startswith("REASONING FAILED"):
                final_action = queue_content_json_str
            else:
                try:
                    queue_data: Dict[str, Any] = json.loads(queue_content_json_str)
                    action_list: list = queue_data.get("actions", [])
                    
                    # Direct write and immediate execution of first action
                    write_result = self.task_manager.save_queue(action_list)
                    self.memory_stream += f"\n[QUEUE DIRECT WRITE] {write_result}"
                    
                    if action_list:
                        final_action = action_list[0]
                    else:
                        final_action = "SLUMBER: 5"
                    
                except json.JSONDecodeError:
                    final_action = f"REASONING FAILED: Failed to decode LLM's JSON response: {queue_content_json_str}"
        
        else:
            final_action = "SLUMBER: 5"
            print(f"Action source: {action_source} not recognized or invalid. Slumbering.")

        # --- 5. Execution and State Update ---
        execution_result = self.execution_layer.execute_action(final_action)
        
        # Pop action from queue
        if action_source == "QUEUE_ACTION" or action_source == "DECOMPOSITION_NEEDED":
            pop_result, self.memory_stream = self.task_manager.pop_next_action(self.memory_stream)
            print(f"QUEUE UPDATE: {pop_result}")
        
        # --- 6. Logging and Memory Update ---
        print(f"ACTION PLANNED: {final_action}")
        print(f"EXECUTION RESULT: {execution_result}")
        log_action(self.constants, cycle_time, final_action, execution_result)
        
        safe_action = str(final_action)
        self.memory_stream = f"Last action: {safe_action[:50]}. Last result: {execution_result[:50]}..."
        
        # Save memory state every cycle
        self.memory_manager.save(self.persistent_memory)

        print(f"[{time.ctime()}] Scion Agent Cycle End.")
        print("-" * 50)
        
        if not self.resources.is_slumbering:
            time.sleep(self.constants['AGENT']['CYCLE_SLEEP_TIME'])

# Entry point for the Agent
if __name__ == "__main__":
    agent = ScionAgent()
    
    while True:
        agent.run_cycle()