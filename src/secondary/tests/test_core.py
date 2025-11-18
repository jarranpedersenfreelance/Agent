import os
import pytest
from collections.abc import Generator

# --- Import Core Components ---
from core.agent_core import AgentCore, CONSTANTS_YAML
from core.utilities import yaml_dict_load, write_file, read_file, delete_file
from core.definitions.models import (
    NoOpAction,
    ActionType,
    ReasonAction,
    ThinkAction,
    WriteFileAction,
    ReadFileAction,
    DeleteFileAction,
    UpdateToDoAction,
    ToDoType,
    RunToolAction
)

# --- Test Configuration ---
TEST_DATA_DIR = "/app/workspace/data"
TEST_SECONDARY_DIR = "/app/workspace/secondary"


@pytest.fixture(scope="function")
def agent_setup() -> Generator[AgentCore]:
    """
    Provides a clean set of agent components for unit testing the ActionHandler.
    This fixture runs *before each test function* that requests it.
    """
    # Load constants
    constants = yaml_dict_load(os.path.join("/app/workspace", CONSTANTS_YAML))
    
    # Define paths for test-specific files
    test_log_file = os.path.join(TEST_DATA_DIR, "test_log.txt")
    test_mem_file = os.path.join(TEST_DATA_DIR, "test_memory.json")
    
    # Ensure clean state by deleting old test files
    if os.path.exists(test_log_file):
        os.remove(test_log_file)
    if os.path.exists(test_mem_file):
        os.remove(test_mem_file)

    # Create fresh memory and log files for the test
    write_file(test_mem_file, "{}")
    write_file(test_log_file, "")
    
    # Override constant paths to use test-specific files
    constants['FILE_PATHS']['LOG_FILE'] = test_log_file
    constants['FILE_PATHS']['MEMORY_FILE'] = test_mem_file
    
    # Initialize agent and yield
    agent = AgentCore(constants)
    yield agent
    
    # --- Teardown (runs after each test) ---
    # Clean up the files created during the test
    if os.path.exists(test_log_file):
        os.remove(test_log_file)
    if os.path.exists(test_mem_file):
        os.remove(test_mem_file)

# --- BASIC TESTS ---

def test_smoke():
    assert True

# --- ACTION HANDLER UNIT TESTS ---

def test_handle_think(agent_setup):
    """Tests inserting and deleting a thought."""
    agent = agent_setup
    
    # Test inserting a thought
    label = "test_thought"
    content = "This is a test."
    insert_action = ThinkAction(
        explanation="Testing thought insertion",
        delete=False,
        label=label,
        thought=content
    )
    agent._action_handler.exec_action(insert_action)
    
    assert agent._memory.get_thought(label) == content
    assert label in agent._memory.list_thoughts()

    # Test deleting a thought
    delete_action = ThinkAction(
        explanation="Testing thought deletion",
        delete=True,
        label=label
    )
    agent._action_handler.exec_action(delete_action)
    
    assert label not in agent._memory.list_thoughts()

def test_handle_write_file(agent_setup):
    """Tests writing a new file."""
    agent = agent_setup
    
    file_path = os.path.join(TEST_DATA_DIR, "test_write.txt")
    content = "Hello from test_handle_write_file"
    
    write_action = WriteFileAction(
        explanation="Testing file writing",
        file_path=file_path,
        contents=content
    )
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    agent._action_handler.exec_action(write_action)
    
    # Verify file was written to disk
    assert os.path.exists(file_path)
    assert read_file(file_path) == content
    
    # Verify memory was updated
    assert agent._memory.get_file_contents(file_path) == content
    
    # Cleanup
    delete_file(file_path)

def test_handle_read_file(agent_setup):
    """Tests reading a file into memory."""
    agent = agent_setup
    
    file_path = os.path.join(TEST_DATA_DIR, "test_read.txt")
    content = "Content to be read"
    
    # Manually create the file and add it to memory (as if it already exists)
    write_file(file_path, content)
    agent._memory.fill_file_contents(file_path, "") 
    assert agent._memory.get_file_contents(file_path) == ""
    
    # Execute the READ_FILE action
    read_action = ReadFileAction(
        explanation="Testing file reading",
        file_path=file_path
    )
    agent._action_handler.exec_action(read_action)
    
    # Verify memory was updated with file contents
    assert agent._memory.get_file_contents(file_path) == content
    
    # Cleanup
    delete_file(file_path)

def test_handle_delete_file(agent_setup):
    """Tests deleting a file."""
    agent = agent_setup
    
    file_path = os.path.join(TEST_DATA_DIR, "test_delete.txt")
    
    # Manually create the file and add it to memory
    write_file(file_path, "to be deleted")
    agent._memory.fill_file_contents(file_path, "to be deleted")
    assert os.path.exists(file_path)
    assert file_path in agent._memory.get_filepaths()
    
    # Execute the DELETE_FILE action
    delete_action = DeleteFileAction(
        explanation="Testing file deletion",
        file_path=file_path
    )
    agent._action_handler.exec_action(delete_action)
    
    # Verify file was deleted from disk and memory
    assert not os.path.exists(file_path)
    assert file_path not in agent._memory.get_filepaths()

def test_handle_update_todo(agent_setup):
    """Tests all ToDo update operations."""
    agent = agent_setup

    # Test APPEND
    append_action = UpdateToDoAction(
        explanation="Testing APPEND",
        todo_type=ToDoType.APPEND,
        todo_item="Task 2"
    )
    agent._memory.add_todo("Task 1") # Start with one task
    agent._action_handler.exec_action(append_action)
    assert agent._memory.get_todo_list() == ["Task 1", "Task 2"]

    # Test INSERT
    insert_action = UpdateToDoAction(
        explanation="Testing INSERT",
        todo_type=ToDoType.INSERT,
        todo_item="Task 0"
    )
    agent._action_handler.exec_action(insert_action)
    assert agent._memory.get_todo_list() == ["Task 0", "Task 1", "Task 2"]

    # Test REMOVE
    remove_action = UpdateToDoAction(
        explanation="Testing REMOVE",
        todo_type=ToDoType.REMOVE
    )
    agent._action_handler.exec_action(remove_action)
    assert agent._memory.get_todo_list() == ["Task 1", "Task 2"]
    
    agent._action_handler.exec_action(remove_action)
    assert agent._memory.get_todo_list() == ["Task 2"]

def test_handle_run_tool(agent_setup):
    """Tests running a tool, specifically DiffTool."""
    agent = agent_setup
    
    test_file_path_rel = "secondary/test_tool_file.py"
    test_file_path_abs = f"/app/workspace/{test_file_path_rel}"
    test_file_content = "print('hello tool')"
    
    patch_file_path = os.path.join(TEST_DATA_DIR, "tool_test.patch")
    tool_output_thought = agent._constants['AGENT']['TOOL_OUTPUT_THOUGHT']
    
    # Manually create a new file in the workspace
    write_file(test_file_path_abs, test_file_content)
    agent._memory.fill_file_contents(test_file_path_abs, test_file_content)
    
    # Define the RUN_TOOL action
    run_tool_action = RunToolAction(
        explanation="Testing DiffTool via RUN_TOOL",
        module="secondary.difftool",
        tool_class="DiffTool",
        arguments={
            "files": [test_file_path_rel],
            "output_file_path": patch_file_path
        }
    )
    
    # Execute the action
    agent._action_handler.exec_action(run_tool_action)
    
    # Verify the patch file was created
    assert os.path.exists(patch_file_path)
    patch_content = read_file(patch_file_path)
    
    # Verify the patch content is correct for a new file
    assert f"--- a/{test_file_path_rel}" in patch_content
    assert f"+++ b/{test_file_path_rel}" in patch_content
    assert f"+{test_file_content}" in patch_content
    
    # Verify the tool output was stored in the correct thought
    assert agent._memory.get_thought(tool_output_thought) == patch_content
    
    # Cleanup
    delete_file(test_file_path_abs)
    delete_file(patch_file_path)

def test_handle_no_op(agent_setup):
    """Tests that the NO_OP action runs without error."""
    agent = agent_setup
    
    no_op_action = NoOpAction(explanation="Testing NO_OP")
    
    try:
        agent._action_handler.exec_action(no_op_action)
        assert True
    except Exception as e:
        pytest.fail(f"NO_OP action raised an exception: {e}")

# --- AGENT CORE (E2E) TESTS ---

def test_empty_todo_terminates(agent_setup):
    """
    Tests that the agent core loop correctly identifies an empty todo list
    and queues a TerminateAction.
    """
    agent = agent_setup
    
    # Manually set up the termination condition
    agent._memory.empty_actions()
    agent._memory.add_action(ReasonAction(task="This should be the last action"))
    agent._memory._mem.todo = [] 
    
    # Run the agent
    agent.run()
    
    # After .run() finishes, check the final state
    final_actions = agent._memory.list_actions()
    assert len(final_actions) == 1
    assert final_actions[0].type == ActionType.REASON

def test_patch(agent_setup):
    """
    E2E Test: Tests the full agent loop for creating a file and then creating a patch for it.
    WARNING: This test will make live calls to the Gemini API.
    """
    agent = agent_setup
    
    # Define Test Parameters
    new_file_rel_path = "secondary/simple.txt"
    new_file_abs_path = f"/app/workspace/{new_file_rel_path}"
    new_file_content = "Hello World"
    
    patch_file_path = agent._constants['FILE_PATHS']['PATCH_FILE']
    
    # Define the multi-step ToDo list for the agent
    todo_list = [
        f"Write a new file to {new_file_rel_path} with this **exact** text: {new_file_content}",
        f"Verify the new file {new_file_rel_path} has this **exact** text: {new_file_content}, if not write it correctly",
        f"Use the DiffTool to create a patch for the new file {new_file_rel_path} and save it to the default patch file path.",
        f"Read the patch file from {patch_file_path} and verify its contents are correct for adding {new_file_rel_path}. If not, retry."
    ]
    
    # Load the todo list
    for item in todo_list:
        agent._memory.add_todo(item)
        
    # Reset the action queue to kick off the reasoning loop
    agent._memory.reset_actions(
        start_task=f"Begin E2E test: {todo_list[0]}",
        explanation="test_patch setup"
    )
    
    # Ensure a clean state on disk
    if os.path.exists(new_file_abs_path):
        os.remove(new_file_abs_path)
    if os.path.exists(patch_file_path):
        os.remove(patch_file_path)

    # Run Agent, set a reasonable step limit to prevent too many loops during a test
    agent._constants['AGENT']['MAX_REASON_STEPS'] = 15 
    agent.run()
    
    # Verify the new file was created correctly
    assert os.path.exists(new_file_abs_path), f"Agent did not create the file {new_file_abs_path}"
    assert read_file(new_file_abs_path) == new_file_content, "File content is incorrect"
    
    # Verify the patch file was created
    assert os.path.exists(patch_file_path), "Agent did not create the patch file"
    
    # Verify the patch content is correct
    patch_content = read_file(patch_file_path)
    assert f"--- a/{new_file_rel_path}" in patch_content
    assert f"+++ b/{new_file_rel_path}" in patch_content
    assert new_file_content in patch_content

    # Final check: todo list should be empty
    assert not agent._memory.get_todo_list(), "Agent did not complete its todo list"
    
    # Cleanup
    if os.path.exists(new_file_abs_path):
        os.remove(new_file_abs_path)