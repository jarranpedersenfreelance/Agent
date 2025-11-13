# tests/test_resource_manager.py
import pytest
from unittest.mock import patch
from datetime import date
from src.core.resource_manager import ResourceManager
from src.core.utilities import write_text_file 
import os

# --- Fixture Setup ---

@pytest.fixture
def resource_manager(mock_constants, setup_file_paths):
    """Fixture to provide a ResourceManager instance."""
    # Ensure constants use the mock state file path
    mock_constants['FILE_PATHS']['RESOURCES_STATE_FILE'] = setup_file_paths['resource']
    rm = ResourceManager(mock_constants)
    rm.clear_state() # Ensure a fresh start
    return rm

# --- Test Cases ---

@patch('src.core.resource_manager.date')
def test_daily_resource_reset_new_day(mock_date, resource_manager):
    """Tests that reasoning count resets when a new day is detected."""
    yesterday = date(2025, 1, 1)
    mock_date.today.return_value = date(2025, 1, 2)
    resource_manager.set_resource('last_run_date', yesterday)
    resource_manager.set_resource('daily_reasoning_count', 0)

    resource_manager._check_daily_reset()
    
    assert resource_manager.get_daily_reasoning_count() == 100
    assert resource_manager.get_resource('last_run_date') == mock_date.today.return_value

def test_record_reasoning_step_success(resource_manager):
    """Tests that a reasoning step is correctly recorded."""
    resource_manager.set_resource('daily_reasoning_count', 10)
    assert resource_manager.record_reasoning_step() is True
    assert resource_manager.get_daily_reasoning_count() == 9

# FIX: Issue 2 Coverage - New Tests for is_file_path_safe
def test_is_file_path_safe_allowed_workspace_files(resource_manager, clean_workspace):
    """Tests that paths within the workspace are considered safe."""
    # Test path is relative to CWD, starting with 'workspace/'
    assert resource_manager.is_file_path_safe("workspace/safe_file.txt") is True
    # Test path is absolute but inside the workspace
    safe_abs_path = os.path.abspath(os.path.join(str(clean_workspace), "workspace/data/test.json"))
    assert resource_manager.is_file_path_safe(safe_abs_path) is True


def test_is_file_path_safe_traversal_denied(resource_manager, clean_workspace):
    """Tests that directory traversal attempts (..) are denied."""
    # Path escaping one level up from CWD (which is tmp_path)
    # The actual CWD is tmp_path, so this is attempting to escape the temp dir.
    # The manager's workspace_dir is tmp_path/workspace.
    assert resource_manager.is_file_path_safe("../external_file.txt") is False 
    
    # Path inside workspace but trying to use traversal to escape
    assert resource_manager.is_file_path_safe("workspace/../external_file.txt") is False


def test_is_file_path_safe_absolute_denied(resource_manager):
    """Tests that absolute paths outside the workspace are denied."""
    # Standard unsafe system paths
    assert resource_manager.is_file_path_safe("/etc/passwd") is False
    assert resource_manager.is_file_path_safe("/usr/bin/python") is False
    
    # Empty string denied
    assert resource_manager.is_file_path_safe("") is False