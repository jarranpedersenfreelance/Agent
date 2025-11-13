# src/core/utilities.py
import os
import json
import yaml
from typing import Any, Dict, List, Union

# --- YAML Utility Functions (Re-implemented for safety and correctness) ---

def yaml_safe_load(file_path: str) -> Union[Dict[str, Any], List[Any]]:
    """
    Safely loads YAML content from a file.
    
    Args:
        file_path: The path to the YAML file.
    
    Returns:
        The deserialized Python object (dict or list).
    
    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        # Use safe_load to prevent arbitrary code execution
        return yaml.safe_load(f)

def yaml_safe_dump(data: Any, file_path: str):
    """
    Safely dumps a Python object to a YAML file.
    
    Args:
        data: The Python object to serialize.
        file_path: The path to the output YAML file.
    """
    # Ensure the directory exists before writing
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        # Use default_flow_style=False for better readability
        yaml.safe_dump(data, f, default_flow_style=False)


# --- JSON Utility Functions ---

def json_load(file_path: str) -> Union[Dict[str, Any], List[Any]]:
    """Loads content from a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def json_dump(data: Any, file_path: str):
    """Dumps content to a JSON file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        # Use indent=4 for human-readable output
        json.dump(data, f, indent=4)


# --- File I/O Utility Functions ---

def read_text_file(file_path: str) -> str:
    """Reads the entire content of a text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def load_file_content(file_path: str, default_content: Union[str, None] = None) -> str:
    """
    Loads text content from a file, returning default content or an error message 
    if the file is not found.
    """
    try:
        # Use existing utility function which raises FileNotFoundError
        return read_text_file(file_path)
    except FileNotFoundError:
        if default_content is not None:
            return default_content
        else:
            return f"Error: File not found at path: {file_path}"

def write_text_file(file_path: str, content: str):
    """Writes content to a text file, creating directories if necessary."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def delete_file(file_path: str):
    """Deletes a file if it exists."""
    if os.path.exists(file_path):
        os.remove(file_path)

def sanitize_filename(filename: str) -> str:
    """Removes or replaces characters that are unsafe or illegal in filenames."""
    # Simple replacement of common bad characters
    safe_name = filename.replace('..', '__').replace('/', '_').replace('\\', '_')
    # Further sanitation can be added here if needed (e.g., restricting length)
    return safe_name