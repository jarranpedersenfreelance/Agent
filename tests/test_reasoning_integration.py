# tests/test_reasoning_integration.py
import unittest
from unittest.mock import MagicMock, patch, call
import os
import json
from src.core.reasoning_integration import ReasoningIntegration
from src.core.models import Action
from pydantic import ValidationError

# Mock constants for initialization
MOCK_CONSTANTS = {
    'API': {'MODEL': 'gemini-test-model'},
    'AGENT': {'CONTEXT_TRUNCATION_LIMIT': 500}
}

class TestReasoningIntegration(unittest.TestCase):

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch('src.core.reasoning_integration.genai.Client')
    def setUp(self, MockClient):
        # Setup Mocks
        self.mock_client = MockClient.return_value
        self.mock_memory_manager = MagicMock()
        
        # Standard Memory Context
        self.mock_memory_manager.get_full_context_for_reasoning.return_value = {
            'development_plan': 'Initial plan.',
            'read_files': {'file1.txt': 'content1'},
            'known_files': ['file1.txt', 'file2.txt'],
            'action_history': ['event 1', 'event 2']
        }
        self.mock_memory_manager.get_development_plan.return_value = 'Initial plan.'
        self.mock_memory_manager.get_known_files.return_value = ['file1.txt', 'file2.txt']

        self.principles = "Always be safe."
        self.syntax = "READ_FILE, EXEC"
        
        # Initialize Integration
        self.integration = ReasoningIntegration(
            constants=MOCK_CONSTANTS,
            principles=self.principles,
            action_syntax=self.syntax,
            memory_manager=self.mock_memory_manager
        )
        self.current_action = Action(type="REASON", payload={"task": "Figure out the next step."})
        
    @patch.dict(os.environ, {}, clear=True)
    def test_initialization_no_api_key(self):
        """Test that initialization fails without API key."""
        with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY environment variable not set"):
            ReasoningIntegration(MOCK_CONSTANTS, "", "", MagicMock())

    def test_build_context_prompt_includes_all_memory(self):
        """Verifies that the prompt contains all necessary memory components."""
        
        prompt = self.integration._build_context_prompt(self.current_action)
        
        # Check for core components
        self.assertIn(self.principles, prompt)
        self.assertIn(self.syntax, prompt)
        self.assertIn(self.current_action.payload['task'], prompt)
        
        # Check for memory stream components
        self.assertIn('Initial plan.', prompt)
        self.assertIn('file1.txt', prompt)
        self.assertIn('event 1', prompt)
        self.assertIn('file2.txt', prompt)
        
        # Check for JSON schema (since it's dynamically generated, check for a key part)
        self.assertIn('Action Pydantic Schema', prompt)
        self.assertIn('"title": "Action"', prompt)

    def test_get_next_actions_success_parsing(self):
        """Mocks a successful LLM call and ensures correct Pydantic parsing."""
        
        # Mock LLM JSON output
        mock_output_list = [
            {"type": "READ_FILE", "payload": {"file_path": "config.yaml"}},
            {"type": "REASON", "payload": {"task": "Verify configuration changes."}}
        ]
        mock_response_text = json.dumps(mock_output_list)
        
        # Configure the mock client response
        mock_response = MagicMock(text=mock_response_text)
        self.mock_client.models.generate_content.return_value = mock_response
        
        # Execute
        actions = self.integration.get_next_actions(self.current_action)
        
        # Assertions
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0].type, "READ_FILE")
        self.assertEqual(actions[1].type, "REASON")
        self.assertEqual(actions[1].payload['task'], "Verify configuration changes.")
        
    def test_get_next_actions_markdown_strip(self):
        """Tests that the handler can strip markdown code block wrapping."""
        
        mock_output_list = [
            {"type": "NOOP", "payload": {}}
        ]
        # Simulate model wrapping JSON in a markdown block
        mock_response_text = f"```json\n{json.dumps(mock_output_list)}\n```"
        
        mock_response = MagicMock(text=mock_response_text)
        self.mock_client.models.generate_content.return_value = mock_response
        
        actions = self.integration.get_next_actions(self.current_action)
        
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].type, "NOOP")

    def test_get_next_actions_invalid_json_handling(self):
        """Tests error handling for non-JSON output."""
        
        mock_response = MagicMock(text="This is not JSON.")
        self.mock_client.models.generate_content.return_value = mock_response
        
        actions = self.integration.get_next_actions(self.current_action)
        
        self.assertEqual(actions, [])
        self.mock_memory_manager.add_event.assert_called()
        self.assertIn("not valid JSON", self.mock_memory_manager.add_event.call_args[0][0])
        
    def test_get_next_actions_pydantic_validation_error(self):
        """Tests error handling for valid JSON but invalid Pydantic schema (e.g., missing mandatory field)."""
        
        # JSON is valid but payload is missing 'file_path' for a READ_FILE, causing validation error
        mock_output_list = [
            {"type": "READ_FILE", "payload": {"invalid_key": "value"}}
        ]
        mock_response_text = json.dumps(mock_output_list)
        
        # Ensure the mock returns text that *will* cause a ValidationError upon parsing
        mock_response = MagicMock(text=mock_response_text)
        self.mock_client.models.generate_content.return_value = mock_response
        
        actions = self.integration.get_next_actions(self.current_action)
        
        self.assertEqual(actions, [])
        self.mock_memory_manager.add_event.assert_called()
        self.assertIn("LLM Action Validation Error", self.mock_memory_manager.add_event.call_args[0][0])