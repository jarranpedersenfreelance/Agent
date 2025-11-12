import json
from typing import Dict, Any

class MemoryManager:
    """Handles loading and saving of structured persistent memory."""
    
    def __init__(self, constants: Dict[str, Any]):
        self.mem_path = constants['PATHS']['MEMORY_FILE']
        self.constants = constants

    def load(self) -> Dict[str, Any]:
        """Loads memory_stream.json into memory."""
        try:
            with open(self.mem_path, 'r') as f:
                memory = json.load(f)
                print("[INFO] Persistent memory loaded successfully.")
                return memory
        except FileNotFoundError:
            print("[INFO] Initializing new persistent memory structure.")
            # Use the existing structure from the snapshot for initialization
            return {
                "read_files": {},
                "development_plan": "Determine best next step of growth based on current goals, codebase, and resources. Self-Update to achieve this growth, and then iterate.",
                "known_files": []
            }
        except Exception as e:
            print(f"[ERROR] Failed to load persistent memory: {e}. Using empty dictionary.")
            return {}

    def save(self, memory_data: Dict[str, Any]) -> str:
        """Saves memory data back to memory_stream.json."""
        try:
            with open(self.mem_path, 'w') as f:
                json.dump(memory_data, f, indent=2)
            return "Success: Persistent memory saved."
        except Exception as e:
            return f"Error: Failed to save persistent memory: {e}"