#!/bin/bash

# --- CONFIGURATION ---
SERVICE_NAME="agent"
CONTAINER_NAME="agent_container"
SNAPSHOT_FILE="codebase_snapshot.txt"
MAX_SNAPSHOT_SIZE=3000000 # ~3 MB (can increase up to 10)

# --- FILE LOCATIONS ---
TEST_REPORT_FILE="test_results.xml"
WORKSPACE_TEST_FILE="workspace/data/$TEST_REPORT_FILE"

# --- HELPER FUNCTIONS ---

function is_running() {
    docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "true"
}

function func_cleanup_output_files() {
    echo "  -> Cleaning previous log and output files..."
    rm -f "$TEST_REPORT_FILE"       # Clear the final XML file from the host root
    rm -f "$WORKSPACE_TEST_FILE"     # Clear the generated XML file from the workspace/data mount
}

function func_logs() {
    echo "--- DUMPING RECENT CONTAINER LOGS FOR '$SERVICE_NAME' ---"
    docker-compose logs --tail=100 --timestamps "$SERVICE_NAME"
    echo "--- LOG DUMP COMPLETE ---"
}

function func_run_all_tests() {
    # This function is used by 'test-deploy'
    if ! is_running; then
        echo "Warning: Cannot run full test suite. Container '$CONTAINER_NAME' is not running."
        return 1
    fi
    
    echo "--- Running Full Test Suite (/app/tests) ---"
    
    # FIX: Changed /usr/bin/python to python3
    docker exec "$CONTAINER_NAME" python3 -m pytest /app/tests --junit-xml="$/app/$WORKSPACE_TEST_FILE"
    TEST_EXIT_CODE=$?

    return $TEST_EXIT_CODE
}

function func_copy_initial_files() {
    # Ensure directories exist
    mkdir -p workspace/core
    mkdir -p workspace/secondary
    mkdir -p workspace/data
    
    # Copy Executable Code
    cp -a src/core/. workspace/core/
    cp -a src/secondary/. workspace/secondary/
    
    # Copy Initial State Files
    cp -R -n src/data/* workspace/data/
    
    # Enforce Immutability (Read-Only Core Logic)
    chmod -R a-w workspace/core/*
    
    # Enforce Read/Write, Non-Executable for Data
    chmod -R a+rw workspace/data/
    # Recursively ensure all files (but not directories) are NOT executable.
    find workspace/data/ -type f -exec chmod a-x {} +
}

# --- CORE DEPLOYMENT LOGIC ---

function func_base_deploy() {
    echo "Ensuring clean slate..."

    # Cleanup Logs
    func_cleanup_output_files

    # Container Management (Stop/Remove Old Instance)
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true

    # Workspace Cleanup (Code Directories)
    rm -rf workspace/core/*
    rm -rf workspace/secondary/*
    
    # Copy Code and Initial State/Data & Set Permissions
    func_copy_initial_files

    # Build and Start
    echo "Building and starting the '$SERVICE_NAME' container..."
    docker-compose up -d --build "$SERVICE_NAME"
}

function func_deploy() {
    echo "--- DEPLOYMENT START: $(date) ---"
    echo ""
    func_base_deploy
    echo ""
    echo "--- DEPLOYMENT END: $(date) ---"
}

function func_test_deploy() {
    echo "--- TEST DEPLOYMENT START: $(date) ---"
    echo ""
    func_base_deploy
    
    # Give the container a moment to start up
    sleep 2 
    
    # Check Container Health and Get Logs on Crash (Initial check)
    if ! is_running; then
        echo "Container failed to remain running (CrashLoop). Dumping logs for root cause analysis."
        func_logs
        
        # Stop container
        echo "Stopping container..."
        docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
        
        # End deployment
        echo "TEST DEPLOYMENT FAILED: Container crashed on startup. Review logs above."
        echo ""
        echo "--- TEST DEPLOYMENT END: $(date) ---"
        return 1 
    fi

    echo "Container is running. Proceeding with tests..."

    func_run_all_tests
    TEST_EXIT_CODE=$?

    if [ "$TEST_EXIT_CODE" -ne 0 ]; then
        # If Pytest failed, check if the container is still running. If not, the main process likely exited.
        if ! is_running; then
            echo "The container crashed during test execution. Dumping logs for root cause analysis."
            func_logs
        fi

        if [ -f "$WORKSPACE_TEST_FILE" ]; then
            echo "Tests failed. Review $TEST_REPORT_FILE"
            cp "$WORKSPACE_TEST_FILE" "$TEST_REPORT_FILE"
        else
            echo "Pytest failed and Test XML file was not generated. See output above for errors."
        fi
    else
        echo "Tests passed."
        cp "$WORKSPACE_TEST_FILE" "$TEST_REPORT_FILE"
    fi

    # Stop container
        echo "Stopping container..."
        docker-compose stop "$SERVICE_NAME" 2>/dev/null || true

    # Final Report
    if [ "$TEST_EXIT_CODE" -eq 0 ]; then
        echo "TEST DEPLOYMENT Complete: ALL TESTS PASSED."
    else
        echo "TEST DEPLOYMENT Complete: TESTS FAILED (Exit Code $TEST_EXIT_CODE). Review $TEST_REPORT_FILE."
    fi

    echo ""
    echo "--- TEST DEPLOYMENT END: $(date) ---"
    return $TEST_EXIT_CODE
}

function func_snapshot() {
    echo "--- SNAPSHOT GENERATION START: $(date) ---"
    rm -f "$SNAPSHOT_FILE"

    echo "Generating Directory Structure..."
    {
        echo "=================================================="
        echo "## PROJECT DIRECTORY STRUCTURE"
        echo "=================================================="
        tree -a -F -I 'workspace|*.git|.env' --noreport 2>/dev/null || (
            echo "Warning: 'tree' command not found. Falling back to 'find/ls'."
            find . -not -path "./workspace/*" -not -path "./.git/*" -not -name "$SNAPSHOT_FILE" -not -name ".env" | sort
        )
        echo ""
    } > "$SNAPSHOT_FILE"

    echo "Compiling File Contents..."
    echo "--- FILE CONTENTS START ---" >> "$SNAPSHOT_FILE"

    find . -type f -not -path "./workspace/*" -not -name "$SNAPSHOT_FILE" -not -path "./.git/*" -not -name ".env" | while IFS= read -r FILE; do
        echo "--- FILE START: $FILE ---" >> "$SNAPSHOT_FILE"
        cat "$FILE" >> "$SNAPSHOT_FILE" || true
        echo -e "\n--- FILE END: $FILE ---\n" >> "$SNAPSHOT_FILE"
    done

    FINAL_SIZE=$(stat -c%s "$SNAPSHOT_FILE" 2>/dev/null || wc -c < "$SNAPSHOT_FILE")
    FINAL_SIZE_MB=$(echo "scale=2; $FINAL_SIZE / 1024 / 1024" | bc)

    echo ""
    echo "Snapshot Complete: $SNAPSHOT_FILE"
    echo "Final Size: $FINAL_SIZE bytes (${FINAL_SIZE_MB} MB)"

    if [ "$FINAL_SIZE" -gt "$MAX_SNAPSHOT_SIZE" ]; then
        echo "WARNING: Final file size exceeds the recommended threshold!"
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
    snapshot)
        func_snapshot
        ;;
    *)
        usage
        exit 1
        ;;
esac