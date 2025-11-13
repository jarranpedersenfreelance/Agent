# tests/test_action_handler.py
import pytest
import os
from unittest.mock import MagicMock, patch
from src.core.action_handler import ActionHandler
from src.core.models import Action
from src.core.utilities import write_text_file

# --- Fixture Setup ---

@pytest.fixture
def action_handler(mock_constants, mock_managers):
    """Fixture to provide a real ActionHandler instance."""
    # The ActionHandler fixture is correctly initialized with 4 arguments (plus self)
    return ActionHandler(mock_constants,
                         mock_managers['memory_manager'],
                         mock_managers['resource_manager'],
                         mock_managers['task_manager'])

@pytest.fixture
def mock_read_file_setup(clean_workspace):
    """Sets up a mock file in the workspace for reading."""
    # Create file inside the 'workspace' sub-directory
    mock_file_path = clean_workspace / "workspace" / "test_file.txt"
    content = "This is the content of the test file."
    write_text_file(str(mock_file_path), content)
    
    # Return the file path as the agent would see it (relative to CWD/tmp_path)
    return "workspace/test_file.txt", str(mock_file_path), content

# --- Test Cases ---

def test_handle_read_file_success(action_handler, mock_read_file_setup, mock_managers):
    """Tests successful execution of READ_FILE action."""
    file_path_raw, _, content = mock_read_file_setup
    
    action = Action(action="READ_FILE", parameters={"file_path": file_path_raw})
    
    expected_result = f"File content:\n--- {file_path_raw} ---\n{content}\n---"
    result = action_handler.execute_action(action)
    
    assert result == expected_result
    # Verify memory update was called with the raw path
    mock_managers['memory_manager'].update_read_files.assert_called_once_with(file_path_raw, content)

# FIX: Issue 6 Coverage - New Test for _resolve_path
def test_internal_path_resolution(action_handler, clean_workspace):
    """Tests that a relative file path is correctly resolved internally."""
    # The CWD is tmp_path, base_dir is tmp_path.
    relative_path = "workspace/data/file.json"
    
    resolved_path = action_handler._resolve_path(relative_path) 
    expected_path = os.path.join(str(clean_workspace), relative_path)
    
    assert os.path.isabs(resolved_path)
    assert resolved_path == os.path.abspath(expected_path)
    
    # Test absolute path (should return itself, just normalized)
    abs_path_in = os.path.abspath("workspace/test.txt")
    assert action_handler._resolve_path(abs_path_in) == abs_path_in


# FIX: Issue 7 Integration Coverage - New Test for security denial
def test_read_file_security_denial(action_handler, mock_managers):
    """Tests that the action is denied if is_file_path_safe returns False."""
    file_path_raw = "unsafe/path/to/secret.txt"
    action = Action(action="READ_FILE", parameters={"file_path": file_path_raw})
    
    # Configure the mock resource manager to deny this path
    mock_managers['resource_manager'].is_file_path_safe.return_value = False
    
    expected_result = f"Error: File path '{file_path_raw}' is unsafe or outside the allowed scope."
    result = action_handler.execute_action(action)
    
    mock_managers['resource_manager'].is_file_path_safe.assert_called_once()
    mock_managers['memory_manager'].update_read_files.assert_not_called()
    assert result == expected_result