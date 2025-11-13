# tests/test_agent_core.py
import pytest
import os
import signal
from unittest.mock import patch, MagicMock
from src.core.agent_core import AgentCore, load_constants, load_agent_principles
from src.core.utilities import yaml_safe_dump, write_text_file

# Define paths relative to the test file location for testing utility functions
TEST_CONSTANTS_PATH = "test_agent_constants.yaml"
TEST_PRINCIPLES_PATH = "test_agent_principles.txt"

# Utility to create a mock YAML constants file
def setup_mock_constants_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    yaml_safe_dump(content, path)

# Utility to create a mock text principles file
def setup_mock_principles_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_text_file(path, content)

# --- Test Cases for Utility Functions ---

def test_load_constants_success(tmp_path, mock_constants):
    """Tests successful loading of structured constants."""
    constants_path = tmp_path / TEST_CONSTANTS_PATH
    setup_mock_constants_file(str(constants_path), mock_constants)
    
    loaded_constants = load_constants(str(constants_path))
    
    # FIX: Issue 9 coverage - check for structured return, not flattened
    assert loaded_constants == mock_constants
    assert 'API' in loaded_constants
    assert loaded_constants['AGENT']['MAX_REASONING_STEPS'] == 100

def test_load_constants_file_not_found(tmp_path):
    """Tests graceful exit on missing constants file."""
    with pytest.raises(SystemExit):
        load_constants(str(tmp_path / "nonexistent.yaml"))

# FIX: Issue 8 Coverage - New Test for principles loading
def test_load_agent_principles_success(tmp_path):
    """Tests successful loading of agent principles."""
    principles_path = tmp_path / TEST_PRINCIPLES_PATH
    mock_content = "Focus on the goal. Be concise."
    setup_mock_principles_file(str(principles_path), mock_content)
    
    loaded_principles = load_agent_principles(str(principles_path))
    assert loaded_principles == mock_content

def test_load_agent_principles_file_not_found(tmp_path):
    """Tests graceful exit on missing principles file."""
    with pytest.raises(SystemExit):
        load_agent_principles(str(tmp_path / "nonexistent.txt"))

# --- Test Cases for AgentCore Class ---

@patch('src.core.agent_core.load_constants')
@patch('src.core.agent_core.load_agent_principles')
@patch('src.core.agent_core.ResourceManager')
@patch('src.core.agent_core.MemoryManager')
@patch('src.core.agent_core.TaskManager')
@patch('src.core.agent_core.ActionHandler')
def test_agent_core_initialization(
    MockActionHandler, 
    MockTaskManager, 
    MockMemoryManager, 
    MockResourceManager, 
    mock_load_principles, 
    mock_load_constants,
    mock_constants # Use the shared mock constants for consistency
):
    """
    Tests that AgentCore initializes all managers correctly with structured constants.
    (Issue 9 coverage)
    """
    mock_load_constants.return_value = mock_constants
    mock_load_principles.return_value = "Test Principles."
    
    # Initialize AgentCore
    core = AgentCore()

    # Assert managers are initialized with the full, structured constants
    # This confirms the removal of the constant flattening logic.
    MockResourceManager.assert_called_once_with(mock_constants)
    MockMemoryManager.assert_called_once_with(mock_constants)
    MockTaskManager.assert_called_once_with(mock_constants)
    
    # Assert ActionHandler is initialized with managers and constants
    MockActionHandler.assert_called_once_with(
        mock_constants, 
        MockMemoryManager(), 
        MockResourceManager(), 
        MockTaskManager()
    )

    # Assert internal constant access is correct
    assert core.AGENT_CONSTANTS == mock_constants['AGENT']
    assert core.FILE_CONSTANTS == mock_constants['FILE_PATHS']
    assert core.principles == "Test Principles."