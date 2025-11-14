import os
import json
import yaml
from typing import Any, Dict, List, Union, Type, TypeVar
from datetime import datetime, timezone
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

# --- YAML Utility Functions ---

def yaml_safe_load(file_path: str) -> Union[Dict[str, Any], List[Any]]:
    """Loads content from a YAML file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def yaml_safe_dump(data: Any, file_path: str):
    """Dumps content to a YAML file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, default_flow_style=False)


# --- JSON Utility Functions ---

def json_typed_load(obj_type: Type[T], file_path: str) -> T:
    """Loads content from a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return obj_type.model_validate_json(f.read())

def json_load(file_path: str) -> Union[Dict[str, Any], List[Any]]:
    """Loads content from a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def json_dump(data: Any, file_path: str):
    """Dumps content to a JSON file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        if (isinstance(data, BaseModel)):
            data = data.model_dump()
        json.dump(data, f, indent=4)


# --- File I/O Utility Functions ---

def read_text_file(file_path: str) -> str:
    """Reads the entire content of a text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_text_file(file_path: str, content: str):
    """Writes content to a text file, creating directories if necessary."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def delete_file(file_path: str):
    """Deletes a file if it exists."""
    if os.path.exists(file_path):
        os.remove(file_path)

# --- Time Utility Functions ---

def current_timestamp():
    return datetime.now(timezone.utc).timestamp()