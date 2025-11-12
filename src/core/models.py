# src/core/models.py

from google.genai import types

# --- STRICT RESPONSE SCHEMA DEFINITION ---
# This schema defines the exact structure for the LLM's output during task decomposition.
# The LLM MUST return a JSON object that strictly adheres to this schema when asked to decompose a task.
# FIX: Changed types.ResponseSchema to the correct types.Schema
ACTION_QUEUE_SCHEMA = types.Schema( 
    type=types.Type.OBJECT,
    properties={
        "actions": types.Schema(
            type=types.Type.ARRAY,
            description=(
                "A strictly ordered list of machine-readable actions to complete the immediate task."
            ),
            items=types.Schema(
                type=types.Type.STRING,
                description=(
                    "One action string in the format: ACTION_TYPE: target [optional content newline].\n"
                    "Valid ACTION_TYPEs and SYNTAX MUST be one of the following exact formats:\n"
                    "1. READ_FILE: [file_path] (e.g., READ_FILE: core/goal.txt)\n"
                    "2. WRITE_FILE: [file_path]\\n[Content body starts here...] (e.g., WRITE_FILE: new_file.py\\ndef test():\\n  pass)\n"
                    "3. RUN_COMMAND: [shell command] (e.g., RUN_COMMAND: ls -R)\n"
                    "4. SLUMBER: [integer_cycles] (e.g., SLUMBER: 10)\n"
                    "5. NEXT_TASK: [new_high_level_task_directive] (e.g., NEXT_TASK: Refactor the execution layer to use a command dictionary.)\n"
                    "NOTE: The NEXT_TASK action MUST be the last item in the actions list. The content following NEXT_TASK: will overwrite immediate_task.txt."
                )
            )
        )
    },
    required=["actions"]
)