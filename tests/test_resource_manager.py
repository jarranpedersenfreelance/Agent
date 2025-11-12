import pytest
from unittest.mock import patch
from datetime import date
from src.core.resource_manager import ResourceManager

# --- RESOURCE MANAGER FIXTURES & TESTS ---

@pytest.fixture
def resource_manager():
    """Fixture for ResourceManager instance."""
    # Since the current ResourceManager is in-memory and relies on constants from the
    # codebase, we initialize it directly.
    return ResourceManager()

def test_initial_state(resource_manager):
    """Tests that the initial state is set correctly from constants."""
    # MAX_REASONING_STEPS is 100 in agent_constants.yaml
    assert resource_manager.get_daily_reasoning_count() == 100 
    assert resource_manager.check_termination_status() is False

def test_record_reasoning_step(resource_manager):
    """Tests successful and failed recording of reasoning steps."""
    # Mock constants.AGENT.MAX_REASONING_STEPS = 100
    initial_count = resource_manager.get_daily_reasoning_count()
    
    # Record one step
    assert resource_manager.record_reasoning_step() is True
    assert resource_manager.get_daily_reasoning_count() == initial_count - 1

    # Record remaining steps until exhaustion
    for _ in range(initial_count - 2):
        resource_manager.record_reasoning_step()
        
    assert resource_manager.get_daily_reasoning_count() == 0

    # Attempt to record when exhausted
    assert resource_manager.record_reasoning_step() is False

def test_check_termination_status(resource_manager):
    """Tests termination status flags."""
    assert resource_manager.check_termination_status() is False
    resource_manager.set_terminated(True)
    assert resource_manager.check_termination_status() is True
    resource_manager.set_terminated(False)
    assert resource_manager.check_termination_status() is False

@patch('src.core.resource_manager.date')
def test_daily_resource_reset(mock_date):
    """Tests that reasoning count resets when a new day is detected."""
    
    # --- Day 1: Exhaust resources ---
    mock_date.today.return_value = date(2025, 11, 12)
    manager = ResourceManager()
    
    # Exhaust reasoning count (100 steps)
    for _ in range(100):
        manager.record_reasoning_step()
        
    assert manager.get_daily_reasoning_count() == 0
    
    # --- Day 2: Load and Reset ---
    mock_date.today.return_value = date(2025, 11, 13)
    
    # New instance simulates agent restart
    new_manager = ResourceManager()
    
    # Assert reset occurred
    assert new_manager.get_daily_reasoning_count() == 100 
    assert new_manager.last_run_date == date(2025, 11, 13)

@patch('src.core.resource_manager.date')
def test_no_resource_reset_on_same_day(mock_date):
    """Tests that reasoning count does NOT reset if on the same day."""
    
    mock_date.today.return_value = date(2025, 11, 12)
    manager = ResourceManager()
    
    # Use one step (100 -> 99)
    manager.record_reasoning_step()
    assert manager.get_daily_reasoning_count() == 99
    
    # Re-initialize on the same day
    new_manager = ResourceManager()
    
    # Assert count did not reset
    assert new_manager.get_daily_reasoning_count() == 99
    assert new_manager.last_run_date == date(2025, 11, 12)