# tests/test_agent_core.py
import unittest
from unittest.mock import MagicMock, patch, call
from src.core.agent_core import AgentCore
from src.core.models import Action

# Mock constants needed for initialization
MOCK_CONSTANTS = {
    'FILE_PATHS': {
        'AGENT_PRINCIPLES_FILE': 'agent_principles.txt',
        'ACTION_SYNTAX_FILE': 'action_syntax.txt'
    },
    'AGENT': {
        'LOOP_SLEEP_SECONDS': 0,
        'STARTING_TASK': 'Initial project analysis task'
    }
}

class TestAgentCore(unittest.TestCase):

    @patch('src.core.agent_core.read_text_file', return_value='content')
    @patch('src.core.agent_core.ResourceManager')
    @patch('src.core.agent_core.MemoryManager')
    @patch('src.core.agent_core.TaskManager')
    @patch('src.core.agent_core.ReasoningIntegration')
    def setUp(self, MockRI, MockTM, MockMM, MockRM, MockRTF):
        # Prevent the sleep call from blocking tests
        self.patcher_sleep = patch('src.core.agent_core.time.sleep')
        self.mock_sleep = self.patcher_sleep.start()
        
        # Setup Mocks
        self.mock_tm = MockTM.return_value
        self.mock_ri = MockRI.return_value
        
        # The agent relies on its ActionHandler. The handler needs a mocked Action.
        # Default side_effect: process one action then stop (unless overridden by specific tests)
        self.mock_action = MagicMock(spec=Action)
        self.mock_tm.dequeue_action.side_effect = [self.mock_action, None]

        # Initialize the core
        self.agent = AgentCore(MOCK_CONSTANTS)

    def tearDown(self):
        self.patcher_sleep.stop()

    def test_agent_core_initialization(self):
        self.assertTrue(hasattr(self.agent, 'memory_manager'))
        self.assertTrue(hasattr(self.agent, 'resource_manager'))
        self.assertTrue(hasattr(self.agent, 'task_manager'))
        self.assertTrue(hasattr(self.agent, 'action_handler'))
        self.assertTrue(hasattr(self.agent, 'reasoning_integration'))
        self.assertEqual(self.agent.agent_principles, 'content')
        self.assertEqual(self.agent.action_syntax, 'content')

    @patch('src.core.agent_core.read_text_file', side_effect=FileNotFoundError)
    @patch('src.core.agent_core.ResourceManager')
    @patch('src.core.agent_core.MemoryManager')
    @patch('src.core.agent_core.TaskManager')
    @patch('src.core.agent_core.ReasoningIntegration')
    def test_load_principles_file_not_found(self, MockRI, MockTM, MockMM, MockRM, MockRTF):
        with self.assertRaises(FileNotFoundError):
            AgentCore(MOCK_CONSTANTS)

    @patch('src.core.agent_core.ActionHandler')
    def test_agent_run_loop_execution(self, MockAH):
        # The default side_effect set in setUp processes one action then stops.
        self.mock_tm.is_queue_empty.return_value = False # Queue is not empty for standard run
        self.agent.run()
        
        # Assert one action was dequeued and handled
        self.mock_tm.dequeue_action.assert_called()
        MockAH.return_value.handle_action.assert_called_once_with(self.mock_action)
        
        # Assert the loop was exited correctly
        self.assertEqual(self.mock_tm.dequeue_action.call_count, 2)
        self.mock_sleep.assert_called_once()
        
    @patch('src.core.agent_core.ActionHandler')
    def test_agent_core_initialization_populates_queue(self, MockAH):
        """Tests that a clean start (empty queue) is populated with a REASON action."""
        
        # 1. Setup TaskManager to report empty queue
        self.mock_tm.is_queue_empty.return_value = True
        
        # 2. Setup the loop to stop after the initial action is added and dequeued
        initial_reason_action = Action(
            type="REASON",
            payload={"task": MOCK_CONSTANTS['AGENT']['STARTING_TASK']}
        )
        # Sequence: Initial check (empty), then dequeuing the action that was just added, then None.
        self.mock_tm.dequeue_action.side_effect = [initial_reason_action, None]
        
        # 3. Run the agent
        self.agent.run()
        
        # 4. Assert initial action was created and added to the queue
        self.mock_tm.add_action.assert_called_once()
        
        # Check the type and payload of the action passed to add_action
        added_action = self.mock_tm.add_action.call_args[0][0]
        self.assertEqual(added_action.type, "REASON")
        self.assertEqual(added_action.payload['task'], MOCK_CONSTANTS['AGENT']['STARTING_TASK'])
        
        # 5. Assert the newly added action was immediately dequeued and handled
        MockAH.return_value.handle_action.assert_called_once()