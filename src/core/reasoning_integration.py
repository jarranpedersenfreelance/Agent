# src/core/reasoning_integration.py
import os
import json
from typing import Any, Dict, List, Union
from google import genai
from google.genai import types
from pydantic import ValidationError
from .models import Action

class ReasoningIntegration:
    """Handles integration with the Gemini API for the agent's reasoning process."""

    def __init__(self, 
                 constants: Dict[str, Any], 
                 principles: str, 
                 action_syntax: str, 
                 memory_manager: Any):
        
        self.constants = constants
        self.memory_manager = memory_manager
        self.model_name = self.constants['API']['MODEL']
        self.agent_principles = principles
        self.action_syntax = action_syntax
        
        # Initialize Gemini Client
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")
            
        self.client = genai.Client(api_key=api_key)
        self.action_schema = Action.model_json_schema()

    def _build_context_prompt(self, current_action: Action) -> str:
        """Constructs the comprehensive prompt for the LLM."""
        
        memory_context = self.memory_manager.get_full_context_for_reasoning()
        
        # Structure the prompt for clarity and goal-orientation
        prompt = f"""
        # Scion Agent Operating Context

        ## 1. Primary Directives (Agent Principles)
        {self.agent_principles}

        ## 2. Current State & Memory
        - **Development Plan:** {self.memory_manager.get_development_plan()}
        - **Current Task (Focus):** {current_action.payload.get('task', 'No specific task defined.')}
        - **File Contents (Read Files):**
        {json.dumps(memory_context['read_files'], indent=2)}
        - **Action History (Last 10 Events):**
        {json.dumps(memory_context['action_history'], indent=2)}
        - **Known Files:** {self.memory_manager.get_known_files()}

        ## 3. Action Syntax and Response Format (CRITICAL)
        Your response MUST be a single JSON list of actions (`List[Action]`).
        The JSON MUST strictly conform to the following schema, which defines the available action types and their payloads:
        
        --- Action Pydantic Schema ---
        {json.dumps(self.action_schema, indent=2)}
        --- End Schema ---
        
        Available Actions:
        {self.action_syntax}
        
        ## 4. Instruction
        Based on the Context, Principles, and the current Task, provide the next logical list of actions (in JSON format) to achieve the overall development plan.
        DO NOT include any explanation or markdown text outside of the single, complete JSON array of actions.
        The work actions (e.g., READ_FILE, EXEC) should precede the final REASON action.
        The last action in your list should ALWAYS be a REASON action (with an updated 'task' payload reflecting the next reasoning step's specific focus) to continue the cycle, unless the project is complete.
        """
        return prompt

    def get_next_actions(self, current_action: Action) -> List[Action]:
        """
        Calls the Gemini API to get the next list of actions and returns them as Pydantic models.
        """
        prompt = self._build_context_prompt(current_action)
        
        # Use a system instruction to guide the model's behavior
        system_instruction = (
            "You are an expert software development AI agent (Scion Agent). "
            "Your sole output must be a single JSON array that adheres strictly "
            "to the provided Action Schema. Do not include any extraneous text, "
            "explanations, or markdown formatting outside of the JSON array itself."
        )
        
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
                config=config,
            )
            
            # The model is instructed to return raw JSON, but often wraps it in a markdown block.
            raw_json_text = response.text.strip()
            if raw_json_text.startswith("```json") and raw_json_text.endswith("```"):
                raw_json_text = raw_json_text[7:-3].strip()

            # Parse the JSON array
            raw_actions_list = json.loads(raw_json_text)
            
            # Validate and convert to Pydantic models
            validated_actions = [Action(**item) for item in raw_actions_list]
            
            return validated_actions
            
        except ValidationError as e:
            error_msg = f"LLM Action Validation Error: {e.errors()}"
            self.memory_manager.add_event(error_msg)
            print(f"ERROR: {error_msg}")
            return [] # Return empty list to stop current cycle
        except json.JSONDecodeError:
            error_msg = f"LLM Output is not valid JSON. Response text start: {response.text[:100]}..."
            self.memory_manager.add_event(error_msg)
            print(f"ERROR: {error_msg}")
            return []
        except Exception as e:
            error_msg = f"Gemini API Error: {e}"
            self.memory_manager.add_event(error_msg)
            print(f"ERROR: {error_msg}")
            return []