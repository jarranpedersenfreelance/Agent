# src/core/models.py

from typing import List, Dict, Any
import json

# Define the action queue schema for the LLM
ACTION_QUEUE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "description": "A list of one or more shell or file operations to execute to move toward the goal.",
            "items": {
                "type": "string",
                "description": (
                    "A single action string formatted as 'COMMAND: [arguments]'. "
                    "Valid commands include: READ_FILE, WRITE_FILE, RUN_COMMAND, SLUMBER, NEXT_TASK, CREATE_DEBUG_SNAPSHOT, and UPDATE_FILE_LIST. "
                    "UPDATE_FILE_LIST takes a file path as an argument (e.g., 'UPDATE_FILE_LIST: data/ls_output.txt') which it parses for file paths, updates persistent memory, and then deletes the source file."
                )
            }
        }
    },
    "required": ["actions"]
}