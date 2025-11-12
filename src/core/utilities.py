import os
import yaml
import json
from typing import Any, Dict, Optional

def load_file_content(path: str, default_content: Optional[str] = None) -> str:
    """Loads content from a file path, or returns a default string if the file is not found."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return default_content if default_content is not None else f"Error: File not found at {path}"

def write_text_file(path: str, content: str) -> bool:
    """Safely writes content to a file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing to file {path}: {e}")
        return False

def yaml_safe_load(path: str) -> Dict[str, Any]:
    """Safely loads YAML content from a file."""
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading YAML from {path}: {e}")
        return {}

def yaml_safe_dump(path: str, data: Dict[str, Any]):
    """Safely dumps YAML content to a file."""
    try:
        with open(path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
    except Exception as e:
        print(f"Error dumping YAML to {path}: {e}")

def json_safe_load(path: str) -> Dict[str, Any]:
    """Safely loads JSON content from a file."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {path}. Returning empty dict.")
        return {}
    except Exception as e:
        print(f"Error loading JSON from {path}: {e}")
        return {}

def json_safe_dump(path: str, data: Dict[str, Any]):
    """Safely dumps JSON content to a file."""
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error dumping JSON to {path}: {e}")