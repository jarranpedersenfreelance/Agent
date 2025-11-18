import os
import json
from typing import Any, Dict, List
from pydantic import BaseModel
from google import genai
from google.genai.errors import APIError

from core.logger import Logger
from core.definitions.models import Action, ReasonAction, SlumberAction
from core.brain.memory import Memory

# --- Pydantic Models for LLM Response Validation ---

# This is the expected root structure of the LLM's JSON response.
class GeminiResponse(BaseModel):
    actions: List[Action]

# This string defines the exact JSON schema the LLM must follow.
SCHEMA_DEFINITION = """
{
  "actions": [
    {
      "type": "REASON",
      "explanation": "<Why you selected this task>",
      "task": "<The task to develop an action plan for>",
      "files_to_send": "<A List[str] of file paths. Only include files that were **newly created/modified** or are **absolutely critical** for the next steps>",
      "thoughts_to_send": "<A List[str] of thought labels. Only include thoughts that contain **contextual information** or **intermediate results** needed for the next steps>"
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
      "explanation": "<Why you are running this tool>",
      "module": "<The python module path, e.g., 'secondary.difftool'>",
      "tool_class": "<The class name of the tool, e.g., 'DiffTool'>",
      "arguments": "<A Dict[str, Any] of arguments. **EXAMPLE for DiffTool**: {'files': ['data/my_first_file.txt', 'secondary/another.py'], 'output_file_path': 'data/update_request.patch'}>"
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
      "use_thought": "<The thought label for the thought content to use as contents. **Must be provided IF and ONLY IF contents is omitted**>",
      "contents": "<Full contents to write. **Must be provided IF and ONLY IF use_thought is omitted**>"
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
        
        self._constants = constants
        self._logger = logger
        self._principles = principles
        self._memory = memory
        self._gemini = Gemini(constants, principles, memory, logger)
    
    def get_next_actions(self, current_action: ReasonAction) -> List[Action]:
        # TODO Add local reasoning before elevating to Gemini
        try:
            return self._gemini.get_next_actions(current_action)
        except Exception as e:
            self._logger.log_error(f"Failed to get next actions from Gemini: {e}")
            return []

class Gemini:
    """Handles integration with the Gemini API for the agent's reasoning process."""

    def __init__(self, 
                 constants: Dict[str, Any], 
                 principles: str, 
                 memory: Memory,
                 logger: Logger):
        
        self._constants = constants
        self._memory = memory
        self._model_name = self._constants['API']['MODEL']
        self._principles = principles
        self._logger = logger
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set. Cannot use REASON action.")

        self._client = genai.Client()

    def _build_context_prompt(self, current_action: ReasonAction) -> str:
        """Constructs the comprehensive prompt for the LLM."""
        
        # Serialize constants
        constants = {
          "MAX_REASON_STEPS": self._constants['AGENT']['MAX_REASON_STEPS']
        }
        constants_content = json.dumps(constants, indent=2)
        
        # Serialize memory
        mem_files = self._memory.get_filepaths()
        selected_memory = {
          "action_queue": self._memory.list_actions(),
          "counters": self._memory.list_counts(),
          "file_contents": {
            k: self._memory.get_file_contents(k) if k in current_action.files_to_send 
            else ""
            for k in mem_files
          },
          "thoughts": {k: self._memory.get_thought(k) for k in current_action.thoughts_to_send},
          "logs": self._memory.load_logs(),
          "todo": self._memory.get_todo_list(),
          "last_memorized": self._memory.last_memorized()
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
{self._principles}

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
(I am only sending the last {self._constants['AGENT']['LOG_TAIL_COUNT']} lines of logs)

# MY CURRENT MEMORY:
{memory_content}
"""
        return prompt

    def get_next_actions(self, current_action: ReasonAction) -> List[Action]:
        """
        Calls the Gemini API to get the next list of actions.
        """
        prompt = self._build_context_prompt(current_action)
        self._logger.log_info(f"Sending prompt to Gemini for task: {current_action.task}")

        try: 
          response = self._client.models.generate_content(
              model=self._model_name,
              contents=prompt,
              config={"response_mime_type": "application/json"}
          )
        except APIError as e:
          if e.code == 503:
            self._logger.log_warning("Gemini service is currently unavailable (503). Queuing SLUMBER and retrying.")
        
          elif e.code == 429:
            self._logger.log_warning("Gemini rate limit exceeded (429). Queuing SLUMBER and retrying.")

          else:
            self._logger.log_warning(f"Unknown Gemini error ({e.code}). Queuing SLUMBER and retrying.")

          new_queue = [
              SlumberAction(
                  seconds=self._constants['AGENT']['GEMINI_WAIT_SECONDS'],
                  explanation="gemini error, waiting to retry"
              ),
              current_action
          ]
            
          return new_queue
        
        response_text = response.text
        self._logger.log_debug(f"Gemini raw response: {response_text}")
        if response_text is not None:
          parsed_response = GeminiResponse.model_validate_json(response_text)
          if parsed_response.actions:
              return parsed_response.actions
        
        self._logger.log_warning("Gemini returned an empty action list.")
        return [] # Will trigger a debug action in core