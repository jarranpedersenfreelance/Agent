#!/bin/bash

# --- CONFIGURATION ---
SERVICE_NAME="agent"
SNAPSHOT_FILE="codebase_snapshot.txt"
# Maximum recommended file size for easy chat upload/processing (in bytes)
MAX_SIZE_BYTES=10485760 # 10 MB

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
    echo "✅ Deployment Complete."
    echo "--- DEPLOYMENT END: $(date) ---"
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


# ==============================================================================
# UPDATED FUNCTION: func_snapshot
# - Now prints directory structure for the entire project (excluding workspace).
# - Now prints contents of all files in the project (excluding files in workspace/).
# - Excludes .git/ and .env file content/listing.
# ==============================================================================
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
        # FIX: Added '|.env' to the -I pattern to exclude the root .env file from the structure listing.
        tree -a -F -I 'workspace|*.git|.env' --noreport 2>/dev/null || (
            echo "Warning: 'tree' command not found. Falling back to 'find/ls'."
            # Use find as a fallback, then filter out the workspace directory, .git directory, and .env file
            find . -not -path "./workspace/*" -not -path "./.git/*" -not -name "$SNAPSHOT_FILE" -not -name ".env" | sort
        )
        echo ""
    } > "$SNAPSHOT_FILE" # Use > to start the file

    # 2. File Contents (Exclude workspace files, .git files, and .env)
    echo "2. Compiling File Contents (Excluding files in workspace/, .git, and .env)..."

    # Find all files recursively, excluding:
    # 1. Any path under ./workspace/
    # 2. The codebase_snapshot.txt file itself
    # 3. The .git directory contents
    # 4. The .env file
    FILE_LIST=$(find . -type f -not -path "./workspace/*" -not -name "$SNAPSHOT_FILE" -not -path "./.git/*" -not -name ".env")

    # The use of 'while read -r FILE' is more robust for paths with spaces than a for loop
    while IFS= read -r FILE; do
        # Do not include the snapshot file itself in the file contents section
        if [[ "$FILE" != "./$SNAPSHOT_FILE" ]]; then
            echo "--- FILE START: $FILE ---" >> "$SNAPSHOT_FILE"
            # Use cat to append content, ensuring a newline at the end of the file content
            cat "$FILE" >> "$SNAPSHOT_FILE" || true
            echo -e "\n--- FILE END: $FILE ---\n" >> "$SNAPSHOT_FILE"
        fi
    done <<< "$FILE_LIST"

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
    echo "  deploy          : Run a full deployment (code update, build, start). (Replaces ./deploy)"
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
    full-reset)
        # FIX #6: Call the new full-reset function
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