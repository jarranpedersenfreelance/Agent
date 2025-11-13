#!/bin/bash

# --- CONFIGURATION ---
SERVICE_NAME="agent"
CONTAINER_NAME="agent_container" # Explicitly defined for docker exec
SNAPSHOT_FILE="codebase_snapshot.txt"
# Maximum recommended file size for easy chat upload/processing (in bytes)
MAX_SIZE_BYTES=10485760 # 10 MB

# --- HELPER FUNCTIONS ---

function is_running() {
    # Check if the primary agent container is running
    docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "true"
}

function func_run_lightweight_tests() {
    # Check if the container is running before attempting to exec
    if ! is_running; then
        echo "⚠️ Warning: Cannot run lightweight tests. Container '$CONTAINER_NAME' is not running."
        return 1
    fi
    
    echo "--- 6. Running Lightweight On-Deploy Tests ---"
    
    # Execute critical unit tests inside the container
    # The tests directory is mounted at /app/tests inside the container.
    docker exec "$CONTAINER_NAME" /usr/bin/python -m pytest /app/tests/test_utilities.py /app/tests/test_resource_manager.py
    TEST_EXIT_CODE=$?

    if [ "$TEST_EXIT_CODE" -eq 0 ]; then
        echo "✅ Lightweight tests passed (Exit Code 0)."
    else
        echo "❌ CRITICAL FAILURE: Lightweight tests FAILED (Exit Code $TEST_EXIT_CODE)."
        echo "Deployment is unstable. Action required."
    fi
    return $TEST_EXIT_CODE
}

function func_run_all_tests() {
    # Check if the container is running before attempting to exec
    if ! is_running; then
        echo "⚠️ Warning: Cannot run full test suite. Container '$CONTAINER_NAME' is not running."
        return 1
    fi
    
    echo "--- Running Full Test Suite (/app/tests) ---"
    
    # Generate JUnit XML report inside the mounted workspace/data directory
    TEST_XML_PATH="/app/workspace/data/test_results.xml"
    
    # Execute ALL tests inside the container, generating the XML report
    # Discard verbose text output to keep the console clean
    docker exec "$CONTAINER_NAME" /usr/bin/python -m pytest /app/tests --junit-xml="$TEST_XML_PATH" > /dev/null 2>&1
    TEST_EXIT_CODE=$?

    # Pass the exit code back to func_test_deploy
    return $TEST_EXIT_CODE
}

# --- CORE FUNCTIONS ---

function func_deploy() {
    echo "--- DEPLOYMENT START: $(date) ---"
    echo ""

    # 1. Robust Container Management (Stop/Remove Old Instance)
    echo "1. Ensuring clean container slate (stopping/removing any running/paused instance)..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true

    # 2. Workspace Cleanup (Code Directories)
    echo "2. Cleaning ALL workspace code/framework directories to prevent clutter..."
    rm -rf workspace/core/*
    rm -rf workspace/secondary/*

    # 3. Copy Source Code (Executable Code)
    echo "3. Copying clean source code to the CORRECT executable directories (workspace/core/ and workspace/secondary/)..."

    # Ensure the executable directories exist directly under workspace
    mkdir -p workspace/core
    mkdir -p workspace/secondary
    mkdir -p workspace/data # Ensures data directory exists for volumes

    # Copy source files for core and secondary logic
    cp -a src/core/. workspace/core/
    cp -a src/secondary/. workspace/secondary/

    # 4. Enforce Immutability (Read-Only Core Logic)
    echo "4. Enforcing Read-Only permissions on Core Logic (workspace/core/)..."
    # Set files to read-only for all users (protects against agent self-modification of core)
    chmod -R a-w workspace/core/*

    # 5. Build and Start
    echo "5. Building and starting the '$SERVICE_NAME' container..."
    docker-compose up -d --build "$SERVICE_NAME"
    echo ""
    
    # 6. Run Lightweight Tests
    func_run_lightweight_tests
    
    # Check test result before declaring deployment successful
    TEST_STATUS=$?
    if [ "$TEST_STATUS" -eq 0 ]; then
        echo "✅ Deployment and Lightweight Tests Complete."
    else
        echo "❌ Deployment completed, but tests FAILED. See output above."
    fi

    echo "--- DEPLOYMENT END: $(date) ---"
}

function func_test_deploy() {
    echo "--- TEST DEPLOYMENT START: $(date) ---"
    echo ""

    # Define the output file name
    TEST_STATUS_YML="test_status.yml"
    TEST_XML_FILE="workspace/data/test_results.xml"

    # 1. Cleanup Logs
    # Note: Assuming func_cleanup_output_files is defined elsewhere and clears workspace/data outputs
    func_cleanup_output_files 
    rm -f "$TEST_STATUS_YML" # Clear the final YML file from the host root
    
    # 2-4: Standard Deployment Setup (Cleanup, Copy, Enforce Immutability)
    echo "1. Ensuring clean container slate (stopping/removing any running/paused instance)..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true

    echo "2. Cleaning ALL workspace code/framework directories to prevent clutter..."
    rm -rf workspace/core/*
    rm -rf workspace/secondary/*

    echo "3. Copying clean source code to the CORRECT executable directories..."
    mkdir -p workspace/core
    mkdir -p workspace/secondary
    mkdir -p workspace/data
    cp -a src/core/. workspace/core/
    cp -a src/secondary/. workspace/secondary/

    echo "4. Enforcing Read-Only permissions on Core Logic (workspace/core/)..."
    chmod -R a-w workspace/core/*

    # 5. Build and Start (Temporarily)
    echo "5. Building and starting the '$SERVICE_NAME' container TEMPORARILY for testing..."
    docker-compose up -d --build "$SERVICE_NAME"
    
    # Give the container a moment to start up
    sleep 2 

    # 6. Run ALL Tests (will generate test_results.xml in workspace/data)
    func_run_all_tests
    TEST_STATUS=$?
    
    # 7. Post-Test Processing: Generate the structured test_status.yml if tests were run
    if [ -f "$TEST_XML_FILE" ]; then
        # This function executes a Python script in the container to convert XML to YML
        func_create_test_status_yml
    else
        echo "⚠️ Warning: Test XML file was not generated or found. Cannot create structured report."
    fi

    # 8. Stop and Remove Temporary Container
    echo "8. Stopping and removing temporary test container..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true
    
    # 9. Clean up temporary XML file if it exists
    rm -f "$TEST_XML_FILE"

    # Final Report
    if [ "$TEST_STATUS" -eq 0 ]; then
        echo "✅ TEST DEPLOYMENT Complete: ALL TESTS PASSED."
    else
        echo "❌ TEST DEPLOYMENT Complete: TESTS FAILED (Exit Code $TEST_STATUS). Review $TEST_STATUS_YML."
    fi

    echo "--- TEST DEPLOYMENT END: $(date) ---"
    return $TEST_STATUS
}

function func_create_test_status_yml() {
    # This Python script is executed inside the container to process the XML
    # and write the structured YAML report to the host's base directory (which is mounted).
    
    # NOTE: This script ASSUMES Python and required libraries (e.g., PyYAML) are available 
    # in the container and the host's base directory is mounted to /app/workspace.

    # 1. Path definitions
    CONTAINER_XML_PATH="/app/workspace/data/test_results.xml"
    HOST_YML_PATH="test_status.yml"
    
    # 2. Python conversion script (executed via docker exec)
    # This uses basic Python XML and YAML libraries (which may need to be installed)
    echo "Running Python script in container to process XML into YAML..."
    docker exec "$CONTAINER_NAME" /usr/bin/python -c "
import xml.etree.ElementTree as ET
import yaml
import os

def parse_junit_xml_to_yaml(xml_path):
    # Check if the XML file exists
    if not os.path.exists(xml_path):
        return {'status': 'FAILED', 'message': f'Test results XML not found at {xml_path}'}
        
    tree = ET.parse(xml_path)
    root = tree.getroot()
    test_suite = root.find('testsuite')
    
    if test_suite is None:
        return {'status': 'FAILED', 'message': 'Invalid test results XML format.'}

    # Extract test status from the XML attributes
    failures = int(test_suite.attrib.get('failures', 0))
    errors = int(test_suite.attrib.get('errors', 0))
    total_tests = int(test_suite.attrib.get('tests', 0))
    
    test_results = []
    
    for testcase in test_suite.findall('testcase'):
        name = testcase.attrib.get('name', 'UNKNOWN')
        classname = testcase.attrib.get('classname', 'UNKNOWN')
        
        test_data = {
            'test': f'{classname}.{name}',
            'status': 'PASSED',
            'error_message': None
        }
        
        # Check for failure/error tags
        failure = testcase.find('failure')
        error = testcase.find('error')
        
        if failure is not None:
            test_data['status'] = 'FAILED'
            test_data['error_message'] = failure.attrib.get('message', 'No message provided.')
            test_data['details'] = failure.text.strip() if failure.text else 'No details.'
        elif error is not None:
            test_data['status'] = 'ERROR'
            test_data['error_message'] = error.attrib.get('message', 'No message provided.')
            test_data['details'] = error.text.strip() if error.text else 'No details.'
        
        test_results.append(test_data)

    output = {
        'status': 'FAILED' if (failures + errors) > 0 else 'PASSED',
        'summary': {
            'total': total_tests,
            'passed': total_tests - failures - errors,
            'failed': failures + errors
        },
        'results': test_results
    }
    
    # Write to a file in the workspace directory, which is mounted to the host
    host_yml_path = os.path.join(os.path.abspath('/app/workspace/'), os.path.basename('$HOST_YML_PATH'))
    with open(host_yml_path, 'w') as f:
        yaml.dump(output, f, sort_keys=False)
    
    print(f'YAML report generated in container at {host_yml_path}')

# Execute the main parsing function
try:
    import yaml
except ImportError:
    print('ERROR: PyYAML library is not installed in the container. Cannot generate YAML report.')
    exit(1)
parse_junit_xml_to_yaml('$CONTAINER_XML_PATH')
    "
}

function func_snapshot() {
    echo "--- SNAPSHOT GENERATION START: $(date) ---"
    rm -f "$SNAPSHOT_FILE" # Clear old snapshot

    # 1. Directory Structure (Exclude workspace, .git/, and .env)
    echo "1. Generating Directory Structure (Excluding workspace/, .git/, and .env)..."
    {
        echo "=================================================="
        echo "## PROJECT DIRECTORY STRUCTURE (Excluding workspace/, .git/, and .env)"
        echo "=================================================="
        # Use tree to generate the full directory structure, ignoring the 'workspace', '.git', and '.env'
        tree -a -F -I 'workspace|*.git|.env' --noreport 2>/dev/null || (
            echo "Warning: 'tree' command not found. Falling back to 'find/ls'."
            # Use find as a fallback, then filter out the workspace directory, .git directory, and .env file
            find . -not -path "./workspace/*" -not -path "./.git/*" -not -name "$SNAPSHOT_FILE" -not -name ".env" | sort
        )
        echo ""
    } > "$SNAPSHOT_FILE" # Use > to start the file

    # 2. File Contents (Exclude workspace files, .git files, and .env)
    echo "2. Compiling File Contents (Excluding files in workspace/, .git, and .env)..."

    # Add the required header before compiling file contents
    echo "--- FILE CONTENTS START ---" >> "$SNAPSHOT_FILE"

    # Find all files recursively, excluding:
    # 1. Any path under ./workspace/
    # 2. The codebase_snapshot.txt file itself
    # 3. The .git directory contents
    # 4. The .env file
    # Use process substitution and pipe for efficiency and to handle paths with spaces
    find . -type f -not -path "./workspace/*" -not -name "$SNAPSHOT_FILE" -not -path "./.git/*" -not -name ".env" | while IFS= read -r FILE; do
        echo "--- FILE START: $FILE ---" >> "$SNAPSHOT_FILE"
        # Use cat to append content
        cat "$FILE" >> "$SNAPSHOT_FILE" || true
        # Ensure a final newline is present after the content
        echo -e "\n--- FILE END: $FILE ---\n" >> "$SNAPSHOT_FILE"
    done

    # --- 3. Final Size Check ---
    FINAL_SIZE=$(stat -c%s "$SNAPSHOT_FILE" 2>/dev/null || wc -c < "$SNAPSHOT_FILE")
    FINAL_SIZE_MB=$(echo "scale=2; $FINAL_SIZE / 1024 / 1024" | bc)

    echo ""
    echo "✅ Snapshot Complete: $SNAPSHOT_FILE"
    echo "Final Size: $FINAL_SIZE bytes (${FINAL_SIZE_MB} MB)"

    if [ "$FINAL_SIZE" -gt "$MAX_SIZE_BYTES" ]; then
        echo "🚨 WARNING: Final file size exceeds the recommended ${MAX_SIZE_BYTES} bytes (10 MB) threshold!"
    fi
}

function func_delete() {
    read -r -p "⚠️ WARNING: This will stop and remove ALL containers, networks, volumes, and THE AGENT IMAGE (scion-agent:latest). Are you sure? (y/N): " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            echo "Deleting all project resources..."
            # Stops and removes containers, networks, volumes, and ALL images defined in docker-compose.yml
            docker-compose down --rmi all
            echo "Deletion complete. Environment is clean."
            ;;
        *)
            echo "Deletion cancelled."
            ;;
    esac
}

function usage() {
    echo "Usage: ./agent_manager.sh <command>"
    echo ""
    echo "Commands:"
    echo "  snapshot        : Generate the codebase_snapshot.txt file for context upload."
    echo "  deploy          : Run a full deployment (code update, build, start) and run lightweight tests."
    echo "  test-deploy     : Run a full deployment setup, execute ALL tests, and cleanup the container. DOES NOT leave agent running."
    echo "  delete          : WARNING: Stops, removes containers, networks, volumes, AND THE AGENT IMAGE."
    echo ""
}

# --- MAIN EXECUTION ---

# Check if a command was provided
if [ -z "$1" ]; then
    usage
    exit 1
fi

case "$1" in
    deploy)
        func_deploy
        ;;
    test-deploy)
        func_test_deploy
        ;;
    snapshot)
        func_snapshot
        ;;
    delete)
        func_delete
        ;;
    *)
        usage
        exit 1
        ;;
esac