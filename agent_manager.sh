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
    
    # Execute ALL tests inside the container
    docker exec "$CONTAINER_NAME" /usr/bin/python -m pytest /app/tests
    TEST_EXIT_CODE=$?

    if [ "$TEST_EXIT_CODE" -eq 0 ]; then
        echo "✅ Full test suite passed (Exit Code 0)."
    else
        echo "❌ Full test suite FAILED (Exit Code $TEST_EXIT_CODE)."
    fi
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

    # 1-4: Standard Deployment Setup (Cleanup, Copy, Enforce Immutability)
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

    # 6. Run ALL Tests
    func_run_all_tests
    TEST_STATUS=$?
    
    # 7. Stop and Remove Temporary Container
    echo "7. Stopping and removing temporary test container..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true
    
    # Final Report
    if [ "$TEST_STATUS" -eq 0 ]; then
        echo "✅ TEST DEPLOYMENT Complete: ALL TESTS PASSED."
    else
        echo "❌ TEST DEPLOYMENT Complete: TESTS FAILED (Exit Code $TEST_STATUS)."
    fi

    echo "--- TEST DEPLOYMENT END: $(date) ---"
    return $TEST_STATUS
}


function func_full_reset() {
    echo "--- FULL RESET START: $(date) ---"
    echo "1. Stopping container..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true

    echo "2. Copying clean state from src/data/ to workspace/data/..."
    # Ensure workspace/data exists
    mkdir -p workspace/data
    # Force copy ALL files from the source of truth for persistent data
    cp -a -f src/data/. workspace/data/

    echo "3. Restarting deployment..."
    func_deploy

    echo "✅ Full Reset Complete."
    echo "--- FULL RESET END: $(date) ---"
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

function usage() {
    echo "Usage: ./agent_manager.sh <command>"
    echo ""
    echo "Commands:"
    echo "  deploy          : Run a full deployment (code update, build, start) and run lightweight tests. (Replaces ./deploy)"
    echo "  test-deploy     : Run a full deployment setup, execute ALL tests, and cleanup the container. DOES NOT leave agent running."
    echo "  full-reset      : Stop container, force copy ALL data/ files from src/data/, then start. (Replaces ./deploy_full_reset)"
    echo "  task-reset      : Stop container, copy ONLY immediate_task.txt, then start. (Replaces ./deploy_reset)"
    echo "  snapshot        : Generate the codebase_snapshot.txt file for context upload. (Replaces ./package)"
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
    full-reset)
        func_full_reset
        ;;
    task-reset)
        echo "--- TASK RESET START: $(date) ---"
        echo "1. Stopping container..."
        docker-compose stop "$SERVICE_NAME" 2>/dev/null || true

        echo "2. Copying immediate_task.txt to workspace/data/..."
        # Ensure workspace/data exists
        mkdir -p workspace/data
        # Copy ONLY immediate_task.txt (and overwrite)
        cp -f src/data/immediate_task.txt workspace/data/

        echo "3. Restarting deployment..."
        # Use deploy function for the clean start
        func_deploy

        echo "✅ Task Reset Complete."
        echo "--- TASK RESET END: $(date) ---"
        ;;
    snapshot)
        func_snapshot
        ;;
    *)
        usage
        exit 1
        ;;
esac