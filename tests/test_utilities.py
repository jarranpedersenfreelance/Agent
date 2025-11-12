import pytest
from pathlib import Path
import json
import yaml
from src.core import utilities
import os

# --- UTILITIES TESTS ---

def test_write_and_read_text_file(tmp_path: Path):
    """Tests writing content to a file and reading it back."""
    test_path = tmp_path / "test.txt"
    test_content = "This is a test file content.\nLine two."
    
    # Write
    utilities.write_text_file(str(test_path), test_content)
    assert test_path.is_file()

    # Read
    # The snapshot's load_file_content strips content, so we ensure comparison also accounts for that.
    read_content = utilities.load_file_content(str(test_path))
    assert read_content.strip() == test_content.strip()

def test_load_nonexistent_file_with_default():
    """Tests loading a non-existent file returns the default content."""
    default = "default content"
    content = utilities.load_file_content("nonexistent_file.txt", default_content=default)
    assert content == default

def test_load_nonexistent_file_without_default():
    """Tests loading a non-existent file returns the standard error message."""
    # Based on the snapshot's utility code, it returns an error string
    content = utilities.load_file_content("nonexistent_file.txt")
    assert content.startswith("Error: File not found")

def test_yaml_safe_dump_and_load(tmp_path: Path):
    """Tests dumping a dictionary to YAML and loading it back."""
    test_path = tmp_path / "test.yaml"
    test_data = {
        "name": "Test Config",
        "settings": {"key": 42, "enabled": True}
    }
    
    # Dump
    utilities.yaml_safe_dump(test_data, str(test_path))
    assert test_path.is_file()

    # Load
    loaded_data = utilities.yaml_safe_load(str(test_path))
    assert loaded_data == test_data

def test_json_dump_and_load(tmp_path: Path):
    """Tests dumping a dictionary to JSON and loading it back."""
    test_path = tmp_path / "test.json"
    test_data = {"id": 1, "status": "active"}

    # Dump
    utilities.json_dump(test_data, str(test_path))
    assert test_path.is_file()

    # Load
    loaded_data = utilities.json_load(str(test_path))
    assert loaded_data == test_data

def test_json_load_nonexistent_file():
    """Tests loading a non-existent JSON file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        utilities.json_load("nonexistent_file.json")

def test_yaml_load_nonexistent_file():
    """Tests loading a non-existent YAML file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        utilities.yaml_safe_load("nonexistent_file.yaml")