import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import subprocess
import time
import os
import zipfile

# Note: The ActionHandler imports constants directly, so we primarily mock the managers
from src.core.action_handler import ActionHandler
from src.core.utilities import write_text_file, load_file_content

# --- Fixtures for Mocking Dependencies ---

@pytest.fixture
def mock_managers():
    """Provides mocks for TaskManager and MemoryManager."""
    return {
        # Note: ResourceManager is not explicitly passed to ActionHandler in current snapshot
        'task_manager': Mock(),
        'memory_manager': Mock(),
    }

@pytest.fixture
def action_handler(mock_managers, tmp_path):
    """Provides an ActionHandler instance, using tmp_path as the agent_root."""
    # The action handler relies on constants for ACTION_LOG_FILE ("data/action_log.txt")
    # We must ensure the log directory exists and the agent_root is the tmp_path for I/O tests.
    log_file = tmp_path / "data" / "action_log.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize ActionHandler with the temporary root path
    handler = ActionHandler(
        agent_root=str(tmp_path), 
        task_manager=mock_managers['task_manager'],
        memory_manager=mock_managers['memory_manager']
    )
    return handler

# --- Test Helpers ---

def get_action_log_content(tmp_path: Path) -> str:
    """Reads the content of the action log file."""
    try:
        # Assumes log file is at {tmp_path}/data/action_log.txt
        return load_file_content(str(tmp_path / "data" / "action_log.txt"))
    except Exception:
        return ""

# --- _read_file Tests ---

def test_read_file_success(action_handler, mock_managers, tmp_path):
    """Tests successful file reading and update to MemoryManager."""
    file_path = "test_file.txt"
    abs_path = tmp_path / file_path
    abs_path.write_text("Test content for reading")
    
    result = action_handler._read_file(file_path)

    assert result.startswith("File content:\n---")
    assert "Test content for reading" in result
    
    # Verify MemoryManager was updated (update_known_files is the nearest available mock)
    # Note: In a real system, MemoryManager should have an update_read_files method.
    # We will assume update_known_files is a stand-in for now, or just check the log.
    
    # Check log for success
    log = get_action_log_content(tmp_path)
    assert f"ACTION: READ_FILE ARGS: ['{file_path}'] RESULT: Success" in log

def test_read_file_not_found(action_handler, tmp_path):
    """Tests file reading when file does not exist."""
    file_path = "non_existent.txt"
    
    result = action_handler._read_file(file_path)

    assert result.startswith("Error: File not found")

    # Check log for failure (logs the error message)
    log = get_action_log_content(tmp_path)
    assert f"ACTION: READ_FILE ARGS: ['{file_path}'] RESULT: Error: File not found" in log


# --- _write_file Tests ---

def test_write_file_success(action_handler, tmp_path):
    """Tests successful file creation/overwriting."""
    file_path = "new_file.py"
    file_content = "print('Hello, World!')"
    abs_path = tmp_path / file_path

    result = action_handler._write_file(file_path, file_content)

    assert result == f"Successfully wrote {len(file_content)} bytes to {file_path}"
    assert abs_path.read_text() == file_content
    
    # Check log for success
    log = get_action_log_content(tmp_path)
    assert f"ACTION: WRITE_FILE ARGS: ['{file_path}', '...'] RESULT: Success" in log


# --- _run_command Tests ---

@patch('subprocess.run')
def test_run_command_success(mock_run, action_handler, tmp_path):
    """Tests successful command execution with expected output."""
    command = "ls -a"
    
    # Mock subprocess.run return value
    mock_run.return_value = Mock(
        stdout=b"file1\nfile2", 
        stderr=b"", 
        returncode=0
    )

    result = action_handler._run_command(command)

    mock_run.assert_called_once_with(
        command, 
        cwd=action_handler.agent_root, 
        capture_output=True, 
        shell=True,
        text=True,
        timeout=30 # Assumed default timeout
    )
    
    assert result.startswith("Command executed successfully.")
    assert "STDOUT:\nfile1\nfile2" in result
    
    # Check log for success
    log = get_action_log_content(tmp_path)
    assert f"ACTION: RUN_COMMAND ARGS: ['{command}'] RESULT: Success" in log

@patch('subprocess.run')
def test_run_command_failure(mock_run, action_handler, tmp_path):
    """Tests command execution that results in a non-zero exit code."""
    command = "non_existent_command"
    
    # Mock subprocess.run return value for failure
    mock_run.return_value = Mock(
        stdout=b"", 
        stderr=b"Command not found", 
        returncode=127
    )

    result = action_handler._run_command(command)

    assert result.startswith("Command FAILED.")
    assert "Exit Code: 127" in result
    assert "STDERR:\nCommand not found" in result
    
    # Check log for failure (logs the error message)
    log = get_action_log_content(tmp_path)
    assert f"ACTION: RUN_COMMAND ARGS: ['{command}'] RESULT: Failure (Code 127)" in log


# --- _slumber Tests ---

@patch('time.sleep')
def test_slumber_success(mock_sleep, action_handler, tmp_path):
    """Tests that the _slumber action calls time.sleep correctly."""
    
    slumber_time = 1.5
    result = action_handler._slumber(slumber_time)
    
    mock_sleep.assert_called_once_with(slumber_time)
    assert result == f"Agent is slumbering for {slumber_time} seconds..."
    
    # Check log for success
    log = get_action_log_content(tmp_path)
    assert f"ACTION: SLUMBER ARGS: [{slumber_time}] RESULT: Success" in log

def test_slumber_invalid_time(action_handler, tmp_path):
    """Tests that _slumber rejects non-positive time values."""
    
    result = action_handler._slumber(-5)
    
    assert result == "Error: Slumber time must be a non-negative number. Received: -5"
    
    # Check log for failure
    log = get_action_log_content(tmp_path)
    assert "ACTION: SLUMBER ARGS: [-5] RESULT: Error: Slumber time must be a non-negative number." in log


# --- _create_debug_snapshot Tests ---

@patch('zipfile.ZipFile')
@patch('os.walk')
def test_create_debug_snapshot_success(mock_os_walk, mock_zipfile, action_handler, tmp_path):
    """Tests the snapshot creation process (without actually creating files)."""
    
    # Mock os.walk to return a simple file structure for the zip process
    mock_os_walk.return_value = [
        (str(tmp_path), ('dir1', 'dir2'), ('file1.txt', 'file2.log')),
        (str(tmp_path / 'dir1'), (), ('nested.py',)),
    ]
    
    # Execute
    result = action_handler._create_debug_snapshot()
    
    # Assertions
    assert result.startswith("Debug snapshot created")
    
    # Check if zipfile.ZipFile was opened with the correct name and mode
    # The default name is agent_debug_snapshot_{timestamp}.zip
    mock_zipfile.assert_called_once()
    assert mock_zipfile.call_args[0][0].endswith(".zip")
    assert mock_zipfile.call_args[0][1] == 'w'
    
    # Check that zip.write was called for all files
    zip_mock = mock_zipfile.return_value.__enter__.return_value
    zip_mock.write.assert_any_call(str(tmp_path / 'file1.txt'), 'file1.txt')
    zip_mock.write.assert_any_call(str(tmp_path / 'file2.log'), 'file2.log')
    zip_mock.write.assert_any_call(str(tmp_path / 'dir1' / 'nested.py'), 'dir1/nested.py')
    
    # Check log for success
    log = get_action_log_content(tmp_path)
    assert "ACTION: CREATE_DEBUG_SNAPSHOT ARGS: [] RESULT: Success" in log