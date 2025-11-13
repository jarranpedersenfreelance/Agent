#!/bin/bash

# --- CONFIGURATION ---
SERVICE_NAME="agent"
CONTAINER_NAME="agent_container" # Explicitly defined for docker exec
SNAPSHOT_FILE="codebase_snapshot.txt"
# Maximum recommended file size for easy chat upload/processing (in bytes)
MAX_SIZE_BYTES=10485760 # 10 MB

# New Test Log Files
TEST_REPORT_FILE="test_results.xml"
WORKSPACE_XML_PATH="workspace/data/$TEST_REPORT_FILE" # Location inside the mounted volume

# --- HELPER FUNCTIONS (DEFINED FIRST TO AVOID "COMMAND NOT FOUND" ERRORS) ---

function is_running() {
    # Check if the primary agent container is running
    docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "true"
}

function func_cleanup_output_files() {
    echo "  -> Cleaning up previous log and output files..."
    # Test Logs
    rm -f "$TEST_REPORT_FILE"       # Clear the final XML file from the host root
    rm -f "$WORKSPACE_XML_PATH"     # Clear the generated XML file from the workspace/data mount
    
    # Runtime Logs
    rm -f workspace/data/runtime_error.log
    rm -f workspace/data/finish_snapshot.txt
}

function func_logs() {
    echo "--- DUMPING RECENT CONTAINER LOGS FOR '$SERVICE_NAME' ---"
    # Show last 100 lines with timestamps
    docker-compose logs --tail=100 --timestamps "$SERVICE_NAME"
    echo "--- LOG DUMP COMPLETE ---"
}

function func_run_lightweight_tests() {
    # This function is used by 'deploy'
    if ! is_running; then
        echo "⚠️ Warning: Cannot run lightweight tests. Container '$CONTAINER_NAME' is not running."
        # Call func_logs to catch any startup error that prevented it from running
        func_logs
        return 1
    fi
    
    echo "--- 6. Running Lightweight On-Deploy Tests ---"
    
    # FIX: Changed /usr/bin/python to python3
    docker exec "$CONTAINER_NAME" python3 -m pytest /app/tests/test_utilities.py /app/tests/test_resource_manager.py
    TEST_EXIT_CODE=$?

    if [ "$TEST_EXIT_CODE" -eq 0 ]; then
        echo "✅ Lightweight tests passed (Exit Code 0)."
    else
        echo "❌ CRITICAL FAILURE: Lightweight tests FAILED (Exit Code $TEST_EXIT_CODE)."
        echo "Attempting to retrieve container logs for diagnosis..."
        func_logs # Dump logs on test failure
        echo "Deployment is unstable. Action required."
    fi
    return $TEST_EXIT_CODE
}

function func_run_all_tests() {
    # This function is used by 'test-deploy'
    if ! is_running; then
        echo "⚠️ Warning: Cannot run full test suite. Container '$CONTAINER_NAME' is not running."
        # Call func_logs to catch any startup error that prevented it from running
        func_logs
        return 1
    fi
    
    echo "--- Running Full Test Suite (/app/tests) ---"
    
    # Generate JUnit XML report inside the mounted workspace/data directory (/app/workspace/data in container)
    CONTAINER_XML_PATH="/app/$WORKSPACE_XML_PATH"
    
    # FIX: Changed /usr/bin/python to python3
    docker exec "$CONTAINER_NAME" python3 -m pytest /app/tests --junit-xml="$CONTAINER_XML_PATH"
    TEST_EXIT_CODE=$?

    return $TEST_EXIT_CODE
}

# ------------------------------
# --- CORE DEPLOYMENT LOGIC ---
# ------------------------------

function func_copy_initial_files() {
    # Ensure directories exist
    mkdir -p workspace/core
    mkdir -p workspace/secondary
    mkdir -p workspace/data
    
    # 1. Copy Executable Code
    echo "3. Copying clean source code (core/ and secondary/)..."
    cp -a src/core/. workspace/core/
    cp -a src/secondary/. workspace/secondary/
    
    # 2. Copy Initial State Files (Fix: Use -n for no-clobber, added -R for robustness)
    echo "3b. Copying all initial data/state files from src/data/ to workspace/data/ (using -n to avoid overwriting existing data)..."
    # Use -n (no-clobber) to prevent overwriting existing files in workspace/data.
    # Added -R (recursive) for robustness when using wildcards.
    cp -R -n src/data/* workspace/data/
    
    # 3. Enforce Immutability (Read-Only Core Logic)
    echo "4. Enforcing Read-Only permissions on Core Logic (workspace/core/)..."
    chmod -R a-w workspace/core/*
    
    # 4. Enforce Read/Write, Non-Executable for Data
    echo "4b. Enforcing Read/Write (non-executable) permissions on Data (workspace/data/)..."
    # Grant read/write to all users recursively (directories gain +x, files typically don't).
    chmod -R a+rw workspace/data/
    # Recursively ensure all files (but not directories) are NOT executable.
    find workspace/data/ -type f -exec chmod a-x {} +
}

function func_deploy() {
    echo "--- DEPLOYMENT START: $(date) ---"
    echo ""
    
    # 1. Cleanup Logs
    func_cleanup_output_files

    # 2. Robust Container Management (Stop/Remove Old Instance)
    echo "1. Ensuring clean container slate (stopping/removing any running/paused instance)..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true

    # 3. Workspace Cleanup (Code Directories)
    echo "2. Cleaning ALL workspace code/framework directories to prevent clutter..."
    rm -rf workspace/core/*
    rm -rf workspace/secondary/*
    
    # 4. Copy Code and Initial State/Data & Set Permissions
    func_copy_initial_files

    # 5. Build and Start
    echo "5. Building and starting the '$SERVICE_NAME' container..."
    docker-compose up -d --build "$SERVICE_NAME"
    echo ""
    
    # 6. Run Lightweight Tests (This will also dump logs on failure)
    func_run_lightweight_tests
    
    TEST_STATUS=$?
    if [ "$TEST_STATUS" -eq 0 ]; then
        echo "✅ Deployment and Lightweight Tests Complete. Agent is now running."
    else
        echo "❌ Deployment completed, but lightweight tests FAILED. Review logs above. Agent is still running but should be considered unstable."
    fi

    echo "--- DEPLOYMENT END: $(date) ---"
}

function func_test_deploy() {
    echo "--- TEST DEPLOYMENT START: $(date) ---"
    echo ""

    # 1. Cleanup Logs
    func_cleanup_output_files
    
    # 2. Robust Container Management (MUST KEEP REMOVE HERE)
    echo "1. Ensuring clean container slate (stopping/removing any running/paused instance)..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true

    # 3. Workspace Cleanup
    echo "2. Cleaning ALL workspace code/framework directories to prevent clutter..."
    rm -rf workspace/core/*
    rm -rf workspace/secondary/*
    
    # 4. Copy Code and Initial State/Data & Set Permissions
    func_copy_initial_files

    # 5. Build and Start (Temporarily)
    echo "5. Building and starting the '$SERVICE_NAME' container TEMPORARILY for testing..."
    docker-compose up -d --build "$SERVICE_NAME"
    
    # Give the container a moment to start up
    sleep 2 

    # 6. Check Container Health and Get Logs on Crash (Initial check)
    if ! is_running; then
        echo ""
        echo "--- 6. CONTAINER CRASH DETECTED ON STARTUP ---"
        echo "❌ Container failed to remain running (CrashLoop). Dumping logs for root cause analysis."
        func_logs # Dump logs immediately on crash detection
        
        # 7. Stop Temporary Container (Leaving container for log inspection) (MODIFIED)
        echo "7. Stopping temporary test container (Leaving container in stopped state for log inspection)..."
        docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
        
        echo "❌ TEST DEPLOYMENT FAILED: Container crashed on startup. Review logs above."
        echo "--- TEST DEPLOYMENT END: $(date) ---"
        return 1 
    fi

    echo "✅ Container is running. Proceeding with tests."

    # 6b. Run ALL Tests (will generate test_results.xml in workspace/data)
    # The 'Error response from daemon' happens here if the main process exits *after* is_running passed.
    func_run_all_tests
    TEST_EXIT_CODE=$?

    # 7. Check if the error was due to a non-running container during exec
    if [ "$TEST_EXIT_CODE" -ne 0 ]; then
        # If Pytest failed, check if the container is still running. If not, the main process likely exited.
        if ! is_running; then
            echo ""
            echo "--- POST-TEST FAILURE: CONTAINER EXITED ---"
            echo "The container crashed during test execution. Dumping logs for root cause analysis."
            func_logs # Dump logs to catch the Python traceback
        fi

        if [ -f "$WORKSPACE_XML_PATH" ]; then
            echo "❌ Tests failed. Copying JUnit XML report to base directory: $TEST_REPORT_FILE"
            cp "$WORKSPACE_XML_PATH" "$TEST_REPORT_FILE"
        else
            echo "⚠️ Warning: Pytest failed and Test XML file was not generated. See output above for errors."
        fi
    else
        echo "✅ Tests passed. Report file not copied to base directory."
    fi

    # 8. Stop Temporary Container (DO NOT REMOVE) (MODIFIED)
    echo "8. Stopping temporary test container (Leaving container in stopped state for log inspection)..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    
    # 9. Clean up temporary XML file from workspace/data
    rm -f "$WORKSPACE_XML_PATH"

    # Final Report
    if [ "$TEST_EXIT_CODE" -eq 0 ]; then
        echo "✅ TEST DEPLOYMENT Complete: ALL TESTS PASSED."
    else
        echo "❌ TEST DEPLOYMENT Complete: TESTS FAILED (Exit Code $TEST_EXIT_CODE). Review $TEST_REPORT_FILE. Container is STOPPED. Use './agent_manager.sh logs' to inspect."
    fi

    echo "--- TEST DEPLOYMENT END: $(date) ---"
    return $TEST_EXIT_CODE
}

function func_delete() {
    # Corrected image name in prompt based on docker-compose.yml image tag: scion-agent:latest
    read -r -p "⚠️ WARNING: This will stop and remove ALL containers, networks, volumes, and THE AGENT IMAGE (scion-agent:latest). Are you sure? (y/N): " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            echo "Deleting all project resources..."
            docker-compose down --rmi all
            echo "Deletion complete. Environment is clean."
            ;;
        *)
            echo "Deletion cancelled."
            ;;
    esac
}

function func_snapshot() {
    echo "--- SNAPSHOT GENERATION START: $(date) ---"
    rm -f "$SNAPSHOT_FILE"

    echo "1. Generating Directory Structure (Excluding workspace/, .git/, and .env)..."
    {
        echo "=================================================="
        echo "## PROJECT DIRECTORY STRUCTURE (Excluding workspace/, .git/, and .env)"
        echo "=================================================="
        tree -a -F -I 'workspace|*.git|.env' --noreport 2>/dev/null || (
            echo "Warning: 'tree' command not found. Falling back to 'find/ls'."
            find . -not -path "./workspace/*" -not -path "./.git/*" -not -name "$SNAPSHOT_FILE" -not -name ".env" | sort
        )
        echo ""
    } > "$SNAPSHOT_FILE"

    echo "2. Compiling File Contents (Excluding files in workspace/, .git, and .env)..."
    echo "--- FILE CONTENTS START ---" >> "$SNAPSHOT_FILE"

    find . -type f -not -path "./workspace/*" -not -name "$SNAPSHOT_FILE" -not -path "./.git/*" -not -name ".env" | while IFS= read -r FILE; do
        echo "--- FILE START: $FILE ---" >> "$SNAPSHOT_FILE"
        cat "$FILE" >> "$SNAPSHOT_FILE" || true
        echo -e "\n--- FILE END: $FILE ---\n" >> "$SNAPSHOT_FILE"
    done

    FINAL_SIZE=$(stat -c%s "$SNAPSHOT_FILE" 2>/dev/null || wc -c < "$SNAPSHOT_FILE")
    FINAL_SIZE_MB=$(echo "scale=2; $FINAL_SIZE / 1024 / 1024" | bc)

    echo ""
    echo "✅ Snapshot Complete: $SNAPSHOT_FILE"
    echo "Final Size: $FINAL_SIZE bytes (${FINAL_SIZE_MB} MB)"

    if [ "$FINAL_SIZE" -gt "$MAX_SIZE_BYTES" ]; then
        echo "🚨 WARNING: Final file size exceeds the recommended ${MAX_SIZE_BYTES} bytes (10 MB) threshold!"
    fi
}

function usage() {
    echo "Usage: ./agent_manager.sh <command>"
    echo ""
    echo "Commands:"
    echo "  deploy          : Run a full deployment and start the agent."
    echo "  test-deploy     : Run a full deployment setup, execute ALL tests, and STOP the container, leaving it available for log inspection."
    echo "  logs            : Display the most recent logs from the agent container."
    echo "  snapshot        : Generate the codebase_snapshot.txt file for context upload."
    echo "  delete          : WARNING: Stops, removes containers, networks, volumes, AND THE AGENT IMAGE."
    echo ""
}

# --- MAIN EXECUTION ---

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
    logs)
        func_logs
        ;;
    delete)
        func_delete
        ;;
    snapshot)
        func_snapshot
        ;;
    *)
        usage
        exit 1
        ;;
esac