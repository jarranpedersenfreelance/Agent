import os
import json
import yaml
from typing import Any, Dict, List, Union, Type, TypeVar
from datetime import datetime, timezone
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

# --- File Scanning Utility Function ---

def scan_workspace(root_dir: str = ".") -> List[str]:
    """
    Recursively scans the directory and returns a list of all file paths 
    relative to the root_dir. Excludes common system/build files.
    """
    file_paths = []
    
    # Define directories/files to ignore in the workspace scan
    IGNORE_DIRS = set(['__pycache__', '.git'])
    IGNORE_FILES = set(['.DS_Store', 'Thumbs.db'])

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out ignored directories in place for os.walk efficiency
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        # Calculate the relative path of the current directory
        relative_dir = os.path.relpath(dirpath, root_dir)
        # os.path.relpath returns '.' for the root, which we should ignore in the join
        if relative_dir == '.':
            relative_dir = ''

        for filename in filenames:
            if filename not in IGNORE_FILES:
                # Construct the full relative path
                if relative_dir:
                    full_path = os.path.join(relative_dir, filename)
                else:
                    full_path = filename
                
                # Normalize the path to use forward slashes for consistency
                file_paths.append(full_path.replace(os.sep, '/'))
                
    return sorted(file_paths)


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