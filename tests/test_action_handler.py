# tests/test_action_handler.py
import unittest
from unittest.mock import MagicMock, patch, call
import os
import shutil
from src.core.action_handler import ActionHandler
from src.core.models import Action
from src.core.utilities import read_text_file

# Constants for Mocks
MOCK_CONSTANTS = {
    'FILE_PATHS': {
        'WORKSPACE_DIR': 'workspace',
        'TASK_QUEUE_FILE': 'data/action_queue.json',
        'ACTION_LOG_FILE': 'data/action_log.txt',
    }
}

class TestActionHandler(unittest.TestCase):

    def setUp(self):
        # Setup workspace for file I/O tests
        self.workspace = MOCK_CONSTANTS['FILE_PATHS']['WORKSPACE_DIR']
        if not os.path.exists(self.workspace):
            os.makedirs(self.workspace)
            
        # Mock dependencies for ActionHandler
        self.mock_mm = MagicMock()  # MemoryManager
        self.mock_rm = MagicMock()  # ResourceManager
        self.mock_tm = MagicMock()  # TaskManager
        self.mock_ri = MagicMock()  # ReasoningIntegration
        
        # Default mock returns
        self.mock_rm.is_file_path_safe.return_value = True
        self.mock_rm.record_reasoning_step.return_value = True
        self.mock_rm.get_daily_reasoning_count.return_value = 99 # Default to plenty of steps left

        # Initialize handler
        self.handler = ActionHandler(self.mock_mm, self.mock_rm, self.mock_tm, self.mock_ri, MOCK_CONSTANTS)

    def tearDown(self):
        # Cleanup workspace
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    # --- ACTION HANDLER CORE TESTS ---

    def test_handle_unknown_action(self):
        action = Action(type="UNKNOWN_ACTION", payload={})
        new_actions = self.handler.handle_action(action)
        self.assertEqual(new_actions, [])
        self.mock_mm.add_event.assert_called_with("Error: Unknown action type: UNKNOWN_ACTION")

    # --- READ_FILE TESTS ---

    @patch('src.core.action_handler.read_text_file', return_value="Test Content")
    def test_handle_read_file_success(self, mock_read):
        file_path = "workspace/test_file.txt"
        action = Action(type="READ_FILE", payload={"file_path": file_path})
        self.handler.handle_action(action)
        
        mock_read.assert_called_once_with(file_path)
        self.mock_mm.update_read_files.assert_called_once_with(file_path, "Test Content")
        self.mock_mm.add_event.assert_called_with(f"Success: Read file {file_path}")

    @patch('src.core.action_handler.read_text_file', side_effect=FileNotFoundError)
    def test_handle_read_file_not_found(self, mock_read):
        file_path = "workspace/nonexistent.txt"
        action = Action(type="READ_FILE", payload={"file_path": file_path})
        self.handler.handle_action(action)
        
        self.mock_mm.update_read_files.assert_not_called()
        self.mock_mm.add_event.assert_called_with(f"Error: File not found at path: {file_path}")

    def test_read_file_security_denial(self):
        file_path = "../../../etc/passwd"
        self.mock_rm.is_file_path_safe.return_value = False
        action = Action(type="READ_FILE", payload={"file_path": file_path})
        
        self.handler.handle_action(action)
        
        self.mock_mm.add_event.assert_called_with("Security Denial: Attempted to read file outside of workspace: ../../../etc/passwd")

    # --- WRITE_FILE TESTS ---

    @patch('src.core.action_handler.write_text_file')
    def test_handle_write_file_success(self, mock_write):
        file_path = "workspace/new_file.py"
        content = "print('hello')"
        action = Action(type="WRITE_FILE", payload={"file_path": file_path, "content": content})
        self.handler.handle_action(action)
        
        mock_write.assert_called_once_with(file_path, content)
        self.mock_mm.add_event.assert_called_with(f"Success: Wrote to file {file_path}")
        
    # --- EXEC TESTS ---
    
    @patch('src.core.action_handler.subprocess.run')
    def test_handle_exec_success(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="ls output", 
            stderr="", 
            returncode=0
        )
        command = "ls -a"
        action = Action(type="EXEC", payload={"command": command})
        self.handler.handle_action(action)
        
        mock_run.assert_called_once()
        self.mock_mm.add_event.assert_any_call("EXEC: Running command: ls -a")
        self.mock_mm.add_event.assert_any_call("Command Output:\nSTDOUT:\nls output\nSTDERR:\n")

    # --- REASON ACTION TESTS (Focus of current fix/feature) ---

    def test_handle_reason_task_validation_failure(self):
        """Tests that REASON fails if 'task' is missing, enforcing the schema."""
        action = Action(type="REASON", payload={"not_a_task": "missing key"})
        
        new_actions = self.handler.handle_action(action)
        
        self.assertEqual(new_actions, [])
        self.mock_ri.get_next_actions.assert_not_called()
        self.mock_mm.add_event.assert_called_with(unittest.mock.ANY) # Check error message was added
        self.assertIn("missing the required 'task' key", self.mock_mm.add_event.call_args[0][0])
        
    def test_handle_reason_llm_updates_task_and_requeues(self):
        """Tests that the LLM's suggested REASON action (with updated task) is correctly requeued."""
        
        # 1. Setup Input Action
        initial_reason = Action(type="REASON", payload={"task": "Old task, must be replaced"})
        
        # 2. Setup LLM Output
        work_action = Action(type="READ_FILE", payload={"file_path": "README.md"})
        next_reason = Action(type="REASON", payload={"task": "New task: Implement core feature"})
        llm_output = [work_action, next_reason]
        self.mock_ri.get_next_actions.return_value = llm_output
        
        # 3. Handle Action
        new_actions = self.handler.handle_action(initial_reason)
        
        # 4. Assertions
        self.assertEqual(len(new_actions), 2)
        # First action is the work action
        self.assertEqual(new_actions[0].type, "READ_FILE")
        # Second action is the REASON action from the LLM
        self.assertEqual(new_actions[1].type, "REASON")
        self.assertEqual(new_actions[1].payload['task'], "New task: Implement core feature")
        self.mock_ri.get_next_actions.assert_called_once_with(initial_reason)

    def test_handle_reason_llm_sends_only_work_actions(self):
        """Tests that if the LLM forgets to send REASON, the original REASON is used for requeue."""
        
        # 1. Setup Input Action
        original_reason = Action(type="REASON", payload={"task": "Original task (LLM failed to update)"})
        
        # 2. Setup LLM Output (No REASON action)
        work_action = Action(type="READ_FILE", payload={"file_path": "config.yaml"})
        llm_output = [work_action]
        self.mock_ri.get_next_actions.return_value = llm_output
        
        # 3. Handle Action
        new_actions = self.handler.handle_action(original_reason)
        
        # 4. Assertions
        self.assertEqual(len(new_actions), 2)
        self.assertEqual(new_actions[0].type, "READ_FILE")
        # Assert the original REASON action was requeued
        self.assertEqual(new_actions[1].type, "REASON")
        self.assertEqual(new_actions[1].payload['task'], "Original task (LLM failed to update)")

    def test_handle_reason_limit_reached_no_requeue(self):
        """Tests that no actions are returned if the daily reasoning limit is exhausted."""
        
        # 1. Setup Resource Manager to fail the check
        self.mock_rm.record_reasoning_step.return_value = False
        
        # 2. Setup Input Action (task validation is skipped if limit is reached first)
        action = Action(type="REASON", payload={"task": "Some task"})
        
        # 3. Handle Action
        new_actions = self.handler.handle_action(action)
        
        # 4. Assertions
        self.assertEqual(new_actions, [])
        self.mock_ri.get_next_actions.assert_not_called()
        self.mock_rm.get_daily_reasoning_count.assert_not_called()
        self.mock_mm.add_event.assert_called_with("Warning: Daily reasoning limit reached. REASON action skipped.")