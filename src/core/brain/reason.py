import os
import json
from typing import Any, Dict, List, Union, Annotated
import google.generativeai as genai
from pydantic import BaseModel, Field

from core.logger import Logger
from core.definitions.models import (
    Action, 
    ActionType, 
    ReasonAction,
    ThinkAction,
    RunToolAction, 
    ReadFileAction, 
    WriteFileAction, 
    DeleteFileAction,
    UpdateToDoAction
)
from core.brain.memory import Memory

# --- Pydantic Models for LLM Response Validation ---

AnyAction = Annotated[
    Union[
      ReasonAction, ThinkAction, RunToolAction, 
      ReadFileAction, WriteFileAction, DeleteFileAction,
      UpdateToDoAction
    ],
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
      "files_to_send": "<A List[str] of file paths that specifies what file contents to send>",
      "thoughts_to_send": "<A List[str] of thought labels that specifies what thought contents to send>"
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
      "module": "<python.tool.module>"
      "tool_class": "<Tool subclass in the specified module>"
      "arguments": "<A Dict[str, Any] of arguments for the Tool execution>"
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
      "use_thought": "Thought label if using corresponding thought value as contents, will be used instead of contents",
      "contents": "<Full contents to write>"
    },
    {
      "type": "DELETE_FILE",
      "explanation": "<Why you are deleting this file>",
      "file_path": "<path/to/file>"
    },
    {
      "type": "UPDATE_TODO",
      "explanation": "<Why you are updating the todo list>",
      "todo_type": "<Literal['INSERT', 'APPEND', 'REMOVE'] that specifies how to update the todo list>"
      "todo_item": "<str content for new list item if doing INSERT (front of queue) or APPEND (back of queue)>"
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
        self.gemini = Gemini(constants, principles, memory, self.logger)
    
    def get_next_actions(self, current_action: ReasonAction) -> List[Action]:
        # TODO Add local reasoning before elevating to Gemini
        try:
            return self.gemini.get_next_actions(current_action)
        except Exception as e:
            self.logger.log_error(f"Failed to get next actions from Gemini: {e}")
            return []

class Gemini:
    """Handles integration with the Gemini API for the agent's reasoning process."""

    def __init__(self, 
                 constants: Dict[str, Any], 
                 principles: str, 
                 memory: Memory,
                 logger: Logger):
        
        self.constants = constants
        self.memory = memory
        self.model_name = self.constants['API']['MODEL']
        self.principles = principles
        self.logger = logger
        
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            self.logger.log_error("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")
            raise ValueError("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name=self.model_name)

    def _build_context_prompt(self, current_action: ReasonAction) -> str:
        """Constructs the comprehensive prompt for the LLM."""
        
        # Serialize constants
        constants = {
          "MAX_REASON_STEPS": self.constants['AGENT']['MAX_REASON_STEPS']
        }
        constants_content = json.dumps(constants, indent=2)
        
        # Serialize memory
        mem_files = self.memory.get_filepaths()
        selected_memory = {
          "action_queue": self.memory.list_actions(),
          "counters": self.memory.list_counts(),
          "file_contents": {
            k: self.memory.get_file_contents(k) if k in current_action.files_to_send 
            else ""
            for k in mem_files
          },
          "thoughts": {k: self.memory.get_thought(k) for k in current_action.thoughts_to_send},
          "logs": self.memory.load_logs(),
          "todo": self.memory.get_todo_list(),
          "last_memorized": self.memory.get_last_memorized()
        }
        memory_content = json.dumps(selected_memory, indent=2)

        # Construct the prompt
        prompt = f"""
I am an AI Agent. Your task is to decide my next actions to take based on the following information.

# YOUR RESPONSE:
You *must* respond with *only* a valid JSON object.
The JSON object must match the schema listed below, containing a single key "actions" which is a list of one or more action objects.
You *must* respond with *at least* one action.
The *last* action in the list *must* be "REASON".

# YOUR RESPONSE SCHEMA:
{SCHEMA_DEFINITION}

# YOUR LOGIC:
Use the memory schema to parse the information in the provided portions of my memory
Use the information in my memory to develop a plan to accomplish my current task
After the current task, I should work on the tasks in my todo list
The plan should adhere to my agent principles
Return the plan as your action list response
NOTE: I will TERMINATE when my todo list is empty, *only* empty todo list after verifying all tasks are truly complete.
IMPORTANT: DO NOT TRY TO WRITE_FILE IN core/ ONLY IN secondary/ OR data/

# MY AGENT PRINCIPLES:
{self.principles}

# MY CURRENT TASK:
{current_action.task}
(This task was assigned with the explanation: "{current_action.explanation}")

# MY CONSTANTS:
{constants_content}

# MY MEMORY SCHEMA
{{
  "action_queue": "<current List[Action] action queue>",
  "counters": "<Dict[str, int] counter variables>",
  "file_contents": "Dict[str, str] that represents complete file structure, relevant file contents",
  "thoughts": "<Dict[str, str] that represents my thoughts>",
  "logs": "<A List[str] of recent log statements>",
  "todo": "<A List[str] that represents my todo list>",
  "last_memorized": "<A str timestamp of the last time my memory was saved to disk>"
}}
(I have all file contents but am only sending those relevant to the task)
(I have more thoughts but am only sending those relevant to the task)
(I am only sending the last {self.constants['AGENT']['LOG_TAIL_COUNT']} lines of logs)

# MY CURRENT MEMORY:
{memory_content}
"""
        return prompt

    def get_next_actions(self, current_action: ReasonAction) -> List[Action]:
        """
        Calls the Gemini API to get the next list of actions.
        """
        prompt = self._build_context_prompt(current_action)
        self.logger.log_info(f"Sending prompt to Gemini for task: {current_action.task}")

        response = self.model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response_text = response.text
        self.logger.log_debug(f"Gemini raw response: {response_text}")
        parsed_response = GeminiResponse.model_validate_json(response_text)
        
        if not parsed_response.actions:
            self.logger.log_warning("Gemini returned an empty action list.")
            return [] # Will trigger a debug action in core
            
        return parsed_response.actions