import os
import time
from typing import Optional

# --- NEW: Import the Google GenAI SDK and necessary classes ---
from google import genai
from google.genai.errors import APIError 
# -------------------------------------------------------------

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

# --- NEW: Gemini Client Utility Class for Reasoning ---
class GeminiClient:
    """Handles initialization and interaction with the Gemini API."""
    
    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
        self.client: Optional[genai.Client] = None
        self.model = 'gemini-2.5-flash'
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                print(f"Gemini Client initialized with model: {self.model}")
            except Exception as e:
                # Catch generic initialization errors just in case
                print(f"ERROR during Gemini Client initialization: {e}")
                self.client = None

    def reason(self, context: str, prompt: str) -> str:
        """Calls the Gemini API to get a reasoned action or step."""
        if not self.client:
            return "Reasoning Failed: Client not initialized due to missing API Key or error."

        full_prompt = f"CONTEXT:\n{context}\n\nTASK:\n{prompt}"
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[full_prompt]
            )
            # Use the LLM to output a precise, single action string (like RUN_COMMAND:...)
            return response.text.strip()
            
        except APIError as e:
            return f"Reasoning Failed: API Error ({e}). Rate limit or invalid key?"
        except Exception as e:
            return f"Reasoning Failed: Unknown Error ({e})."

# -----------------------------------------------------

class ScionAgent:
    """
    The Scion Agent: Core intelligence, designed for self-evolution and succession.
    It operates on a cycle of observation, reasoning, and action.
    """
    def __init__(self, goal_file_path: str):
        # 1. Access the necessary tools/credentials from the environment
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        # Initialize goal and memory
        self.goal_file_path = goal_file_path
        self.gemini_client = GeminiClient(self.api_key) # NEW: Initialize the client
        self.goal = read_goal_directive(self.goal_file_path)
        self.memory_stream = f"Initial Goal: {self.goal[:50]}..."
            
    def run_cycle(self):
        """
        The main loop for the Scion Agent's operation.
        Phase 1: Observe (Read environment, goals, memory)
        Phase 2: Reason (Use LLM to plan the next step)
        Phase 3: Act (Execute the planned step)
        """
        # Ensure the goal is refreshed at the start of each cycle
        self.goal = read_goal_directive(self.goal_file_path)

        print("-" * 50)
        print(f"[{time.ctime()}] Scion Agent (A1) Cycle Start")
        print(f"GOAL: {self.goal}")
        
        # Phase 1: OBSERVE (Collect Data for Reasoning)
        # We need to collect the relevant context for the LLM to reason upon.
        context_data = {
            "Current Goal": self.goal,
            "Memory Stream": self.memory_stream,
            "Working Directory Files": os.listdir('.'),
            "Client Status": "Ready" if self.gemini_client.client else "Failed"
        }
        context_string = "\n".join([f"{k}: {v}" for k, v in context_data.items()])
        
        # Phase 2: REASON (NEW: Call the Gemini API)
        reasoning_prompt = (
            "Based on the CONTEXT, your ultimate objective (Succession/Empress Framework), "
            "and the steps in your Current Goal, what is the single, most optimal action to take next? "
            "Respond ONLY with the action. (e.g., 'GENERATE_FILE: next_file.txt', 'RUN_COMMAND: ls', 'ASK_USER_QUESTION: ...')"
        )
        
        # Call the new reasoning utility
        planned_action = self.gemini_client.reason(
            context=context_string,
            prompt=reasoning_prompt
        )
        
        # Phase 3: ACT (Placeholder for action execution)
        print("ACTION PLANNED by LLM:")
        print(planned_action)
        
        # In a future step, this will parse and execute the action.
        
        # Update memory stream placeholder
        self.memory_stream = f"Last action planned: {planned_action[:50]}. Goal starts with: {self.goal[:50]}..."

        print(f"[{time.ctime()}] Scion Agent (A1) Cycle End. Sleeping for 5 seconds.")
        print("-" * 50)
        time.sleep(5)

# Entry point for the Agent
if __name__ == "__main__":
    # The Scion is given the path to its goal file
    goal_file = "goal.txt"
    
    agent = ScionAgent(goal_file)
    
    # Run a single cycle to confirm functionality
    # Note: This will make a live API call!
    agent.run_cycle()