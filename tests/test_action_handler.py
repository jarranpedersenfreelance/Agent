import pytest
from unittest.mock import MagicMock, call
import os
import shutil

# FIX: Corrected the imported function name from 'load_file_content' to the actual function 'read_text_file'
from src.core.utilities import write_text_file, read_text_file 
from src.core.resource_manager import ResourceManager
from src.core.action_handler import ActionHandler
from src.core.models import Action

# Mock Constants
MOCK_CONSTANTS = {
    'GOAL_FILE': 'core/goal.txt',
    'REASONING_PRINCIPLES_FILE': 'core/reasoning_principles.txt'
}

@pytest.fixture
def mock_managers():
    """Fixture to provide mocked managers for ActionHandler."""
    return {
        'memory_manager': MagicMock(),
        'task_manager': MagicMock()
    }

@pytest.fixture
def resource_manager(tmp_path):
    """Fixture to provide a real ResourceManager instance."""
    # Create a simple constants dict for ResourceManager
    constants = {'RESOURCES_STATE_FILE': str(tmp_path / "resource_state.yaml")}
    return ResourceManager(constants)


@pytest.fixture
def action_handler(resource_manager, mock_managers):
    """Fixture to provide a real ActionHandler instance."""
    # ActionHandler expects all managers and constants
    return ActionHandler(MOCK_CONSTANTS, 
                         mock_managers['memory_manager'], 
                         resource_manager, 
                         mock_managers['task_manager'])

# --- Test Cases for File Management Actions (READ, WRITE, DELETE) ---

def test_read_file_success(action_handler, mock_managers, tmp_path):
    """Tests the READ_FILE action on an existing file."""
    test_file = tmp_path / "test.txt"
    test_content = "File content: TEST"
    write_text_file(str(test_file), test_content)

    action = Action(action_type="READ_FILE", file_path="test.txt")
    action_handler.resource_manager.is_file_path_safe = MagicMock(return_value=True)
    
    # Mock the read operation to ensure it reads from the correct temporary path
    # NOTE: Since read_text_file uses the OS, this is a real file read using the fixture's path.
    
    result = action_handler.handle_read_file(action)
    
    expected_output = f"File content:\n--- test.txt ---\n{test_content}\n---"
    assert result == expected_output
    action_handler.resource_manager.is_file_path_safe.assert_called_once_with("test.txt")
    mock_managers['memory_manager'].update_read_files.assert_called_once()


def test_read_file_not_found(action_handler, tmp_path):
    """Tests the READ_FILE action on a non-existent file."""
    action = Action(action_type="READ_FILE", file_path="nonexistent.txt")
    action_handler.resource_manager.is_file_path_safe = MagicMock(return_value=True)
    
    result = action_handler.handle_read_file(action)
    
    expected_output = "Error: File 'nonexistent.txt' not found."
    assert result == expected_output
    action_handler.resource_manager.is_file_path_safe.assert_called_once_with("nonexistent.txt")


def test_read_file_unsafe_path(action_handler):
    """Tests the READ_FILE action on an unsafe path."""
    action = Action(action_type="READ_FILE", file_path="/etc/passwd")
    action_handler.resource_manager.is_file_path_safe = MagicMock(return_value=False)
    
    result = action_handler.handle_read_file(action)
    
    expected_output = "Error: File path '/etc/passwd' is unsafe or outside the allowed scope."
    assert result == expected_output
    action_handler.resource_manager.is_file_path_safe.assert_called_once_with("/etc/passwd")


# --- Test Cases for Action Execution ---

def test_execute_action_read_file(action_handler):
    """Tests the main execute_action method calling handle_read_file."""
    action = Action(action_type="READ_FILE", file_path="test.txt")
    
    # Mock the underlying handler to control output
    action_handler.handle_read_file = MagicMock(return_value="READ SUCCESS")
    
    result = action_handler.execute_action(action)
    
    assert result == "READ SUCCESS"
    action_handler.handle_read_file.assert_called_once_with(action)


def test_execute_action_unknown_type(action_handler):
    """Tests the main execute_action method with an unknown action type."""
    action = Action(action_type="UNKNOWN_ACTION", file_path="test.txt")
    
    result = action_handler.execute_action(action)
    
    assert result.startswith("Error: Unknown action type 'UNKNOWN_ACTION'")

# --- Additional tests for other actions (WRITE, DELETE, etc.) would follow here ---