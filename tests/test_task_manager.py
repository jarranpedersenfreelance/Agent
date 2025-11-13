# tests/test_task_manager.py
import pytest
import os
from src.core.task_manager import TaskManager
from src.core.utilities import json_load, json_dump

# --- Fixture Setup ---

@pytest.fixture
def task_manager(mock_constants, setup_file_paths):
    """Fixture to provide a TaskManager instance."""
    # Ensure constants use the mock state file path
    queue_file_path = setup_file_paths['queue']
    mock_constants['FILE_PATHS']['ACTION_QUEUE_FILE'] = queue_file_path
    
    # Clear the file before starting
    if os.path.exists(queue_file_path):
        os.remove(queue_file_path)
        
    tm = TaskManager(mock_constants)
    return tm

# --- Test Cases ---

# FIX: Issue 5 Coverage - New Test for current_task logic
def test_task_manager_initial_state_and_update(task_manager, mock_constants):
    """Tests that current_task initializes from constants and can be updated."""
    initial_task = mock_constants['AGENT']['STARTING_TASK']
    
    # Test initial load
    assert task_manager.get_current_task() == initial_task
    
    # Test update
    new_task = "Implement all missing Pydantic validation."
    task_manager.update_current_task(new_task)
    assert task_manager.get_current_task() == new_task

# FIX: Issue 4 Coverage - New Test for queue operations
def test_task_queue_operations(task_manager):
    """Tests the core enqueue, dequeue, and status methods."""
    action1 = {'action': 'READ_FILE', 'parameters': {'file_path': 'test1.txt'}}
    action2 = {'action': 'WRITE_FILE', 'parameters': {'file_path': 'test2.txt'}}

    # 1. Initial state
    assert task_manager.has_pending_actions() is False
    assert task_manager.dequeue_action() is None

    # 2. Enqueue
    task_manager.enqueue_action(action1)
    task_manager.enqueue_action(action2)
    assert task_manager.has_pending_actions() is True

    # 3. Dequeue (FIFO)
    dequeued_action = task_manager.dequeue_action()
    assert dequeued_action == action1
    assert task_manager.has_pending_actions() is True
    
    dequeued_action = task_manager.dequeue_action()
    assert dequeued_action == action2
    assert task_manager.has_pending_actions() is False

# FIX: Issue 4 Coverage - New Test for persistence
def test_task_manager_persistence(task_manager, setup_file_paths, mock_constants):
    """Tests that the action queue is correctly saved and loaded."""
    action = {'action': 'REFINE_PLAN', 'parameters': {}}
    
    # 1. Enqueue in first instance
    task_manager.enqueue_action(action)
    assert os.path.exists(setup_file_paths['queue']) # Check file created

    # 2. Create new instance to trigger load
    reloaded_manager = TaskManager(mock_constants)
    
    # 3. Check loaded state
    assert reloaded_manager.has_pending_actions() is True
    dequeued_action = reloaded_manager.dequeue_action()
    assert dequeued_action == action
    
    # 4. Check if the file was correctly updated by the reloaded manager (should be empty)
    final_queue_content = json_load(setup_file_paths['queue'])
    assert final_queue_content == []