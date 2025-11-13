# src/core/utilities.py
import json
import yaml
import os
from typing import Any, Dict, List, Union # FIX: Added typing imports for clarity and NameError prevention

def json_dump(data: Union[Dict, List], path: str) -> None:
    """Dumps a Python object to a JSON file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        raise IOError(f"Error dumping JSON data to file '{path}': {e}") from e

def json_load(path: str) -> Union[Dict, List]:
    """Loads data from a JSON file. Raises FileNotFoundError if the file is missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"JSON file not found: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from file '{path}': {e}") from e
    except IOError as e:
        raise IOError(f"Error loading JSON data from file '{path}': {e}") from e

def yaml_dump(data: Any, path: str) -> None:
    """Dumps a Python object to a YAML file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False)
    except IOError as e:
        raise IOError(f"Error dumping YAML data to file '{path}': {e}") from e

def yaml_load(path: str) -> Any:
    """Loads data from a YAML file. Raises FileNotFoundError if the file is missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"YAML file not found: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Error decoding YAML from file '{path}': {e}") from e
    except IOError as e:
        raise IOError(f"Error loading YAML data from file '{path}': {e}") from e

def read_text_file(path: str) -> str:
    """Reads content from a plain text file. Raises FileNotFoundError if the file is missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Text file not found: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError as e:
        raise IOError(f"Error reading text file '{path}': {e}") from e

def write_text_file(path: str, content: str) -> None:
    """Writes content to a plain text file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except IOError as e:
        raise IOError(f"Error writing text file to '{path}': {e}") from e

def sanitize_filename(filename: str) -> str:
    """Strips common path traversal and non-portable characters from a filename."""
    # This is a basic sanitizer
    filename = filename.strip()
    filename = filename.replace('../', '').replace('./', '')
    filename = filename.replace('/', os.sep).replace('\\', os.sep)
    return filename