# tests/conftest.py
import pytest
import os
import shutil
from unittest.mock import MagicMock
from src.core.models import Action

# --- Shared Constants Fixture (Issue 10 Refactoring) ---

@pytest.fixture
def mock_constants():
    """Provides structured mock constants mirroring the YAML structure."""
    return {
        "FILE_PATHS": {
            "ACTION_QUEUE_FILE": "data/action_queue.json",
            "MEMORY_STREAM_FILE": "data/memory_stream.json",
            "RESOURCES_STATE_FILE": "data/resource_state.yaml"
        },
        "API": {
            "MODEL": "gemini-2.5-flash",
        },
        "AGENT": {
            "LOOP_SLEEP_SECONDS": 0.5,
            "MAX_REASONING_STEPS": 100,
            "CONTEXT_TRUNCATION_LIMIT": 50, # Small limit for easy truncation testing (Issue 3)
            "STARTING_TASK": "Begin self-improvement cycle."
        }
    }

# --- Shared Environment/File Fixtures (Issue 2) ---

@pytest.fixture
def clean_workspace(tmp_path):
    """
    Creates a temporary 'workspace' directory for file I/O tests 
    and changes the CWD to the tmp_path root for path resolution integrity.
    """
    # Create the 'workspace' folder inside the temporary directory
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir(exist_ok=True)
    
    # Create the 'data' folder
    data_path = workspace_path / "data"
    data_path.mkdir(exist_ok=True)
    
    # Change the CWD to the temporary path for consistent path resolution in managers
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    yield tmp_path # Provide the root temporary path

    # Restore CWD after the test
    os.chdir(original_cwd)

@pytest.fixture
def setup_file_paths(clean_workspace, mock_constants):
    """Returns the absolute paths for the state files based on the mock constants."""
    file_paths = {
        'resource': str(clean_workspace / mock_constants['FILE_PATHS']['RESOURCES_STATE_FILE']),
        'memory': str(clean_workspace / mock_constants['FILE_PATHS']['MEMORY_STREAM_FILE']),
        'queue': str(clean_workspace / mock_constants['FILE_PATHS']['ACTION_QUEUE_FILE']),
    }
    return file_paths

# --- Shared Mock Objects ---

@pytest.fixture
def mock_managers():
    """Provides mock manager objects for use in testing components."""
    # Mock is_file_path_safe to allow most paths by default, for isolation
    mock_resource = MagicMock()
    mock_resource.is_file_path_safe.return_value = True 
    
    return {
        'memory_manager': MagicMock(),
        'resource_manager': mock_resource,
        'task_manager': MagicMock()
    }

@pytest.fixture
def mock_action_read():
    """Returns a mock Pydantic Action object for READ_FILE."""
    return Action(
        action="READ_FILE",
        parameters={"file_path": "test_file.txt"}
    )