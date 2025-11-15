import os
import json
from typing import Any, Dict, List, Union, Annotated
import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError

from core.logger import Logger
from core.definitions.models import (
    Action, 
    ActionType, 
    ReasonAction,
    ThinkAction,
    RunToolAction, 
    ReadFileAction, 
    WriteFileAction, 
    DeleteFileAction
)
from core.brain.memory import Memory

# --- Pydantic Models for LLM Response Validation ---

AnyAction = Annotated[
    Union[ReasonAction, ThinkAction, RunToolAction, ReadFileAction, WriteFileAction, DeleteFileAction, Action],
    Field(discriminator='type')
]

# This is the expected root structure of the LLM's JSON response.
class GeminiResponse(BaseModel):
    actions: List[AnyAction]

# This string defines the exact JSON schema the LLM must follow.
SCHEMA_DEFINITION = """
{
  "actions": [
    {
      "type": "REASON",
      "explanation": "<Why you selected this task>",
      "task": "<The task to develop an action plan for>",
      "files_to_send": "<A JSON List[str] of file paths that specifies what file contents to send>",
      "thoughts_to_send": "<A JSON List[str] of thought labels that specifies what thought contents to send>"
    },
    {
      "type": "THINK",
      "explanation": "<Why you are inserting, modifying, or deleting this thought>",
      "delete": "<The bool value for if you are deleting the thought or not>",
      "label": "<The thought index>",
      "thought": "<The thought contents>"
    },
    {
      "type": "RUN_TOOL",
      "explanation": "<Why you selected this task>",
      "module_path": "<path/to/file>"
      "tool class": "<Type for the Tool>"
      "arguments": "<A JSON [str, Any] dictionary of arguments>"
    },
    {
      "type": "READ_FILE",
      "explanation": "<Why you are reading this file>",
      "file_path": "<path/to/file>"
    },
    {
      "type": "WRITE_FILE",
      "explanation": "<Why you are writing this file>",
      "file_path": "<path/to/file>",
      "contents": "<Full contents to write>"
    },
    {
      "type": "DELETE_FILE",
      "explanation": "<Why you are deleting this file>",
      "file_path": "<path/to/file>"
    }
  ]
}
"""

class Reason:
    """Serves as the Agents reasoning."""
    def __init__(self, 
                 constants: Dict[str, Any], 
                 logger: Logger,
                 principles: str, 
                 memory: Memory):
        
        self.constants = constants
        self.logger = logger
        self.principles = principles
        self.memory = memory
        # Pass the logger instance to the Gemini class
        self.gemini = Gemini(constants, principles, memory, self.logger)
    
    def get_next_actions(self, current_action: ReasonAction) -> List[Action]:
        # TODO Add local reasoning before elevating to Gemini
        try:
            return self.gemini.get_next_actions(current_action)
        except Exception as e:
            self.logger.log_error(f"Failed to get next actions from Gemini: {e}")
            # Return an empty list to trigger the debug action in agent_core
            return []

class Gemini:
    """Handles integration with the Gemini API for the agent's reasoning process."""

    def __init__(self, 
                 constants: Dict[str, Any], 
                 principles: str, 
                 memory: Memory,
                 logger: Logger): # Added logger
        
        self.constants = constants
        self.memory = memory
        self.model_name = self.constants['API']['MODEL']
        self.principles = principles
        self.logger = logger # Store the logger
        
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            self.logger.log_error("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")
            raise ValueError("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")
        
        # Configure the genai library
        genai.configure(api_key=self.api_key)
        
        # Set up the model
        self.model = genai.GenerativeModel(model_name=self.model_name)

    def _build_context_prompt(self, current_action: ReasonAction) -> str:
        """Constructs the comprehensive prompt for the LLM."""
        
        # Serialize the file contents from memory
        try:
            # We only include file_contents, not the full memory object
            memory_content = json.dumps(self.memory.memory.file_contents, indent=2)
        except Exception as e:
            self.logger.log_error(f"Failed to serialize memory for prompt: {e}")
            memory_content = "{}" # Fallback to empty JSON

        # Construct the prompt
        prompt = f"""
You are an AI agent. Your task is to decide the next actions to take based on your principles, your memory, and your current task.

# AGENT PRINCIPLES:
{self.principles}

# CURRENT MEMORY (File Contents):
{memory_content}

# CURRENT TASK:
{current_action.arguments.task}
(This task was assigned with the explanation: "{current_action.explanation}")

# YOUR RESPONSE:
You *must* respond with *only* a valid JSON object.
The JSON object must match the following schema, containing a single key "actions" which is a list of one or more action objects.
The *last* action in the list *must* be a "REASON" action for the next step.

# SCHEMA:
{SCHEMA_DEFINITION}
"""
        return prompt

    def get_next_actions(self, current_action: ReasonAction) -> List[Action]:
        """
        Calls the Gemini API to get the next list of actions.
        """
        prompt = self._build_context_prompt(current_action)
        self.logger.log_debug(f"Sending prompt to Gemini for task: {current_action.arguments.task}")

        try:
            # Request JSON output
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            response_text = response.text
            self.logger.log_debug(f"Gemini raw response: {response_text}")

            # Parse and validate the JSON response
            parsed_response = GeminiResponse.model_validate_json(response_text)
            
            if not parsed_response.actions:
                self.logger.log_warning("Gemini returned an empty action list.")
                return [] # Will trigger a debug action in core

            # Validate that the last action is REASON
            if parsed_response.actions[-1].type != ActionType.REASON:
                self.logger.log_warning("Gemini response did not end with a REASON action. Appending one.")
                parsed_response.actions.append(
                    ReasonAction(
                        explanation="Default action because LLM response did not end with REASON.",
                        arguments={"task": "Review and correct the previous action plan."}
                    )
                )
                
            # Return the list of Pydantic Action objects
            return parsed_response.actions

        except ValidationError as e:
            self.logger.log_error(f"Failed to validate Gemini JSON response: {e}")
            self.logger.log_debug(f"Invalid JSON received: {response_text}")
            # Let the exception propagate to be handled by agent_core
            raise
        
        except Exception as e:
            self.logger.log_error(f"Error calling Gemini API: {e}")
            # Let the exception propagate
            raise