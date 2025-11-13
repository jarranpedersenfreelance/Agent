# tests/test_memory_manager.py
import pytest
from src.core.memory_manager import MemoryManager
from src.core.utilities import write_text_file, json_load, delete_file
import os

# --- Fixture Setup ---

@pytest.fixture
def memory_manager(mock_constants, setup_file_paths):
    """Fixture to provide a MemoryManager instance."""
    # Ensure constants use the mock state file path
    mem_file_path = setup_file_paths['memory']
    mock_constants['FILE_PATHS']['MEMORY_STREAM_FILE'] = mem_file_path
    
    # Ensure the file is deleted before the test runs
    if os.path.exists(mem_file_path):
        os.remove(mem_file_path)
        
    mm = MemoryManager(mock_constants)
    return mm

# --- Test Cases ---

def test_initial_load_creates_default_state(memory_manager):
    """Tests that the initial state loads correctly when the file doesn't exist."""
    stream = memory_manager.memory_stream
    assert 'read_files' in stream
    assert 'development_plan' in stream
    assert stream['known_files'] == []

def test_update_development_plan_and_persistence(memory_manager):
    """Tests that the development plan can be updated and saved."""
    new_plan = "Refactor Task Manager for better queue persistence."
    memory_manager.update_development_plan(new_plan)
    
    # Create a new manager instance to force a reload
    reloaded_manager = MemoryManager(memory_manager.constants)
    assert reloaded_manager.get_development_plan() == new_plan

# FIX: Issue 3 Coverage - New Tests for update_read_files and truncation
def test_update_read_files_no_truncation(memory_manager):
    """Tests that content shorter than the limit is saved entirely (limit=50)."""
    content = "This is short content, only 30 characters long."
    file_path = "src/core/models.py"
    
    memory_manager.update_read_files(file_path, content)
    
    read_context = memory_manager.get_read_files_context()
    assert file_path in read_context
    assert read_context[file_path] == content

def test_update_read_files_at_truncation_limit(memory_manager):
    """Tests that content exactly at the limit is saved entirely (limit=50)."""
    content = "A" * 50 
    file_path = "src/core/limit_file.py"
    
    memory_manager.update_read_files(file_path, content)
    
    read_context = memory_manager.get_read_files_context()
    assert read_context[file_path] == content
    assert len(read_context[file_path]) == 50

def test_update_read_files_with_truncation(memory_manager):
    """Tests that content longer than the limit is truncated and marked (limit=50)."""
    long_content = "A" * 100 
    file_path = "src/core/test_file.py"
    expected_content = "A" * 50 + "..."
    
    memory_manager.update_read_files(file_path, long_content)
    
    read_context = memory_manager.get_read_files_context()
    assert file_path in read_context
    assert read_context[file_path] == expected_content
    assert len(read_context[file_path]) == 53 # 50 chars + "..."