import os
import json
import yaml
import collections
from typing import Any, Dict, List, Union, Type, TypeVar
from datetime import datetime, timezone
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

# --- File Scanning Utility Function ---

def scan_files(base_dir: str = '/app/', ignore_list: List[str] = []) -> List[str]:
    """Returns absolute file paths for all files in the specified directory"""
    base_path = os.path.abspath(base_dir)
    file_paths: List[str] = []
    
    for root, dirs, files in os.walk(base_path, topdown=True):
        dirs[:] = [d for d in dirs if d not in ignore_list]

        for filename in files:
            absolute_path = os.path.join(root, filename)
            
            if not filename in ignore_list:
                path_segments = absolute_path.split(os.sep)
                if any(segment in ignore_list for segment in path_segments):
                    is_ignored = True
                file_paths.append(absolute_path)
                          
    return file_paths


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

def read_file(file_path: str) -> str:
    """Reads the entire content of a file (utf-8)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path: str, content: str):
    """Writes content to a file, creating directories if necessary (utf-8)."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def append_file(file_path: str, content: str):
    """Appends to an existing file (utf-8)."""
    if os.path.exists(file_path):
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)

def delete_file(file_path: str):
    """Deletes a file if it exists."""
    if os.path.exists(file_path):
        os.remove(file_path)

def read_file_tail(file_path: str, x: int) -> List[str]:
    """ Reads the last x lines of a file using a deque for efficiency."""
    with open(file_path, 'r') as f:
        last_lines = collections.deque(f, x)
    return list(last_lines)

# --- Time Utility Functions ---

def current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")