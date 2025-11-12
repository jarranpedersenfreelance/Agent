import os
import time
import re
import json 
from google import genai
from google.genai.errors import APIError
from typing import Optional, List, Dict, Any

from . import agent_constants as constants
from .resource_manager import ResourceManager
from .task_manager import TaskManager 
from .memory_manager import MemoryManager
from .action_handler import ActionHandler
from .utilities import load_file_content, yaml_safe_load, yaml_safe_dump

class GeminiClient:
    """Manages the connection and API calls to the Gemini model."""

    def __init__(self, api_key: Optional[str]): # Issue 7: Made api_key direct argument
        """Initializes the Gemini Client."""
        try:
            if not api_key:
                raise ValueError("API Key is required but was not provided.")
            
            self.client = genai.Client(api_key=api_key)
            print("Gemini Client initialized successfully.")

        except Exception as e:
            print(f"Error initializing Gemini Client: {e}")
            self.client = None 

    def generate_decomposition(self, prompt: str) -> Optional[str]:
        """Generates a text response from the model based on the prompt."""
        if not self.client:
            print("Client is not initialized. Cannot generate decomposition.")
            return None

        try:
            response = self.client.models.generate_content(
                model=constants.API.MODEL,
                contents=prompt
            )
            return response.text
        except APIError as e:
            print(f"API Error during generation: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during generation: {e}")
            return None


class AgentCore:
    """The central loop and control flow for the Self-Evolving Agent."""

    def __init__(self, agent_root: str = constants.FILE_PATHS.ROOT, api_key: Optional[str] = None):
        self.agent_root = agent_root
        
        # Issue 7: Centralized API Key lookup
        key = api_key if api_key else os.environ.get("GEMINI_API_KEY")
        self.gemini_client = GeminiClient(api_key=key) 

        # Initialize Managers
        self.resources = ResourceManager()
        self.task_manager = TaskManager(agent_root=self.agent_root)
        self.memory_manager = MemoryManager(agent_root=self.agent_root)
        
        # Initialize ActionHandler and absorb ExecutionLayer's role (Issue 2)
        self.action_handler = ActionHandler(
            agent_root=self.agent_root,
            task_manager=self.task_manager,
            memory_manager=self.memory_manager
        )
        self.is_running = True
        self._sync_resources_from_persistent_memory()

    # --- Persistence ---
    
    def _sync_resources_from_persistent_memory(self):
        """Loads the agent's mutable state from the persistent memory file."""
        path = os.path.join(self.agent_root, constants.FILE_PATHS.RESOURCES_STATE_FILE)
        data = yaml_safe_load(path)
        self.resources.from_dict(data)
        print(f"Resources loaded: {self.resources.daily_reasoning_count} steps remaining.")

    def _sync_resources_to_persistent_memory(self):
        """Saves the agent's mutable state to the persistent memory file."""
        path = os.path.join(self.agent_root, constants.FILE_PATHS.RESOURCES_STATE_FILE)
        data = self.resources.to_dict()
        yaml_safe_dump(path, data)

    # --- Prompt Building (Issue 3: Split into helpers) ---

    def _get_context_memory(self) -> str:
        """Formats memory stream and known files for the context prompt."""
        memory_stream = self.memory_manager.memory 
        return json.dumps({
            "development_plan": memory_stream.get("development_plan", "No Development Plan"),
            "known_files_count": len(memory_stream.get("known_files", []))
        }, indent=2)
        
    def _get_context_history(self) -> str:
        """Loads and truncates the action log for the context prompt."""
        action_log = load_file_content(os.path.join(self.agent_root, constants.FILE_PATHS.ACTION_LOG_FILE), "NO ACTIONS LOGGED.")
        
        if len(action_log) > constants.AGENT.CONTEXT_TRUNCATION_LIMIT:
            action_log = action_log[-constants.AGENT.CONTEXT_TRUNCATION_LIMIT:]
            action_log = f"...[TRUNCATED HISTORY]\n{action_log}"
            
        return action_log

    def _build_context_prompt(self) -> str:
        """Constructs the context section of the agent's reasoning prompt."""
        
        goal = load_file_content(os.path.join(self.agent_root, constants.FILE_PATHS.GOAL_FILE), "NO PROJECT GOAL DEFINED.")
        immediate_task = self.task_manager.get_immediate_task()
        action_queue_str = json.dumps(self.task_manager.action_queue, indent=2)

        prompt_parts = [
            "--- CONTEXT ---",
            f"PROJECT GOAL (From goal.txt):\n{goal}",
            f"\nIMMEDIATE TASK (From immediate_task.txt):\n{immediate_task}",
            f"\nAGENT MEMORY (Plan, File Count):\n{self._get_context_memory()}",
            f"\nACTION QUEUE (From action_queue.json):\n{action_queue_str}",
            f"\nACTION HISTORY (Last {constants.AGENT.CONTEXT_TRUNCATION_LIMIT} chars from action_log.txt):\n{self._get_context_history()}",
            "---------------",
        ]
        
        return "\n".join(prompt_parts)

    def _build_reasoning_prompt(self, context_prompt: str) -> str:
        """Constructs the full prompt for the LLM, including principles and context."""
        
        principles = load_file_content(os.path.join(self.agent_root, constants.FILE_PATHS.REASONING_PRINCIPLES_FILE), "DEFAULT REASONING PRINCIPLES: Always choose the next best action.")
        
        full_prompt = (
            f"AGENT PRINCIPLES:\n{principles}\n\n"
            f"{context_prompt}\n\n"
            "CURRENT STATUS:\n"
            f"You have {self.resources.daily_reasoning_count} reasoning steps remaining before termination.\n\n"
            "--- INSTRUCTIONS ---"
            "Based on the CONTEXT and your PRINCIPLES, determine the *single* next action to take."
            "The action MUST be on the first line, followed by your reasoning in subsequent lines."
            "The action must strictly adhere to the ACTION SYNTAX (e.g., READ_FILE: filename)."
            "--------------------"
        )
        return full_prompt

    # --- Main Loop ---
    
    def run_cycle(self):
        """Executes a single reasoning and action step."""
        
        if not self.resources.can_reason():
            print("Termination condition reached: Max reasoning steps exceeded for the day.")
            self.is_running = False
            return
        
        action_from_queue = self.task_manager.pop_next_action()
        
        if action_from_queue:
            print(f"--- ACTION FROM QUEUE ---\n{action_from_queue}")
            
            # Action from queue is a string like "ACTION_TYPE: arg1 arg2"
            parsed_action = self.action_handler._parse_action_line(action_from_queue)
            action_type = parsed_action["type"]
            args = parsed_action["args"]
        else:
            context_prompt = self._build_context_prompt()
            reasoning_prompt = self._build_reasoning_prompt(context_prompt)
            
            decomposition = self.gemini_client.generate_decomposition(reasoning_prompt)
            self.resources.record_reasoning_step()

            if decomposition is None:
                print("Reasoning failed (API Error/Client Not Ready). Slumbering briefly.")
                self.action_handler.execute_action("SLUMBER", [str(constants.AGENT.LOOP_SLEEP_SECONDS * 2)], log=False)
                return

            print(f"--- LLM DECOMPOSITION (Action + Reasoning) ---\n{decomposition}")

            # Issue 2: Direct parsing of the decomposition's first line
            parsed_action = self.action_handler._parse_action_line(decomposition.split('\n')[0])
            
            if not parsed_action:
                 print("Execution Error: Could not parse a valid action from the LLM output.")
                 self.action_handler.execute_action("SLUMBER", [str(constants.AGENT.LOOP_SLEEP_SECONDS * 2)], log=False)
                 return
                 
            action_type = parsed_action["type"]
            args = parsed_action["args"]

        # Execute the determined action
        action_result = self.action_handler.execute_action(action_type, args)

        print(f"--- ACTION RESULT ---\n{action_result}")
        
        self._sync_resources_to_persistent_memory()
        
        if not action_result.startswith("Success: Slumbered for"):
             time.sleep(constants.AGENT.LOOP_SLEEP_SECONDS)

    def run(self):
        """The main execution loop of the agent."""
        print("Starting Agent Core loop...")
        while self.is_running:
            self.run_cycle()
            
        print("Agent Core loop terminated.")

if __name__ == "__main__":
    try:
        # AgentCore handles API key retrieval from environment if not provided
        core = AgentCore(agent_root="./")
        core.run()
    except Exception as e:
        print(f"CRITICAL ERROR: Agent failed to run: {e}")