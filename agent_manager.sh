#!/bin/bash

# --- CONFIGURATION ---
SERVICE_NAME="agent"
SNAPSHOT_FILE="codebase_snapshot.txt"
# Maximum recommended file size for easy chat upload/processing (in bytes)
MAX_SIZE_BYTES=10485760 # 10 MB

# --- CORE FUNCTIONS (Existing) ---

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
    mkdir -p workspace/data

    # Copy source files for core and secondary logic
    cp -a src/core/. workspace/core/
    cp -a src/secondary/. workspace/secondary/

    # 4. Enforce Immutability (Read-Only Core Logic)
    echo "4. Enforcing Read-Only permissions on Core Logic (workspace/core/)..."
    # Set files to read-only (444) for user, group, and others.
    chmod 444 workspace/core/*

    # 5. Operational Data Persistence Logic
    echo "5. Syncing operational data structure to workspace/data/ (copying only new/missing files)..."

    # Iterate over all files in src/data/ and copy them ONLY if they do not exist
    for data_file in src/data/*; do
        if [ -f "$data_file" ]; then
            filename=$(basename "$data_file")
            target_path="workspace/data/$filename"

            if [ ! -f "$target_path" ]; then
                echo "Copying new data file: $filename"
                cp "$data_file" "$target_path"
            else
                echo "Data file already exists: $filename (Retained for persistence)"
            fi
        fi
    done

    # 6. Build and Run Docker Container
    echo "6. Building and running Docker container..."
    docker-compose up --build -d

    echo ""
    echo "--- DEPLOYMENT COMPLETE ---"
}

function func_full_reset() {
    echo "--- DEPLOYMENT FULL RESET (ALL DATA) START: $(date) ---"

    # 1. Stop the running container
    echo "1. Stopping the Agent container..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true

    # 2. Overwrite ALL data files
    echo "2. Forcing copy of ALL files from src/data/ to workspace/data/..."
    # The -a flag ensures metadata is preserved, -f ensures overwrite.
    cp -af src/data/. workspace/data/

    # 3. Restart the container
    echo "3. Restarting the Docker container..."
    docker-compose start "$SERVICE_NAME"

    echo "--- DEPLOYMENT FULL RESET COMPLETE ---"
}

function func_task_reset() {
    echo "--- DEPLOYMENT RESET (IMMEDIATE TASK) START: $(date) ---"

    # 1. Stop the running container
    echo "1. Stopping the Agent container..."
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true

    # 2. Overwrite the immediate task file
    echo "2. Forcing copy of fresh src/data/immediate_task.txt to workspace/data/..."
    cp -f src/data/immediate_task.txt workspace/data/immediate_task.txt

    # 3. Restart the container
    echo "3. Restarting the Docker container..."
    docker-compose start "$SERVICE_NAME"

    echo "--- DEPLOYMENT RESET COMPLETE ---"
}

function func_snapshot() {
    echo "📦 Generating codebase snapshot to $SNAPSHOT_FILE..."
    # Clear the existing output file
    > "$SNAPSHOT_FILE"

    # --- 1. Print Directory Structure ---
    echo "==================================================" >> "$SNAPSHOT_FILE"
    echo "## PROJECT DIRECTORY STRUCTURE" >> "$SNAPSHOT_FILE"
    echo "==================================================" >> "$SNAPSHOT_FILE"
    if command -v tree &> /dev/null
    then
        tree -a -I 'workspace|__pycache__|.git' >> "$SNAPSHOT_FILE"
    else
        echo "NOTE: 'tree' command not found. Using 'ls -R' for directory structure." >> "$SNAPSHOT_FILE"
        ls -R | grep -v 'workspace\|__pycache__\|\.git' >> "$SNAPSHOT_FILE"
    fi
    echo "" >> "$SNAPSHOT_FILE"

    # --- 2. Print File Contents (Excluding workspace and hidden files) ---
    echo "==================================================" >> "$SNAPSHOT_FILE"
    echo "## FILE CONTENTS" >> "$SNAPSHOT_FILE"
    echo "==================================================" >> "$SNAPSHOT_FILE"

    find . -type f -not -path './workspace/*' \
                    -not -path './.git/*' \
                    -not -name "$SNAPSHOT_FILE" \
                    -not -name 'agent_manager.sh' \
                    -not -name 'package' \
                    -not -name 'deploy' \
                    -not -name 'deploy_reset' \
                    -not -name 'deploy_full_reset' \
                    -not -name '.*' | sort | while read -r FILE_PATH; do

        echo "" >> "$SNAPSHOT_FILE"
        echo "--- FILE START: $FILE_PATH ---" >> "$SNAPSHOT_FILE"
        echo "" >> "$SNAPSHOT_FILE"
        cat "$FILE_PATH" >> "$SNAPSHOT_FILE"
        echo "" >> "$SNAPSHOT_FILE"
        echo "--- FILE END: $FILE_PATH ---" >> "$SNAPSHOT_FILE"

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

# --- NEW FUNCTION FOR AGENT DEBUG TRIGGER ---
function func_debug_snapshot() {
    TASK_FILE="workspace/data/immediate_task.txt"
    SRC_TASK_FILE="src/data/immediate_task.txt"

    echo "--> Triggering Agent Debug Snapshot..."

    # 1. Write the action to the source task file for persistence/cleanliness
    echo "CREATE_DEBUG_SNAPSHOT:" > "$SRC_TASK_FILE"
    echo "--> Action 'CREATE_DEBUG_SNAPSHOT:' written to source file $SRC_TASK_FILE."

    # 2. Force the immediate execution file to be updated for the running agent
    echo "--> Forcing copy of the action to the runtime task file ($TASK_FILE) for immediate execution..."
    cp -f "$SRC_TASK_FILE" "$TASK_FILE"
    
    # 3. Inform user of next step
    echo "--> The Agent will execute this in the next cycle and save the full state to workspace/data/debug_snapshot.txt."
    echo "--> The file will be immediately available in your workspace/data directory."
}
# ---------------------------------------------


function usage() {
    echo "Usage: ./agent_manager.sh <command>"
    echo ""
    echo "Commands:"
    echo "  deploy          : Run a full deployment (code update, build, start). (Replaces ./deploy)"
    echo "  full-reset      : Stop container, force copy ALL data/ files from src/data/, then start. (Replaces ./deploy_full_reset)"
    echo "  task-reset      : Stop container, copy ONLY immediate_task.txt, then start. (Replaces ./deploy_reset)"
    echo "  snapshot        : Generate the codebase_snapshot.txt file for context upload. (Replaces ./package)"
    echo "  debug-snapshot  : **NEW** Trigger the Agent to execute CREATE_DEBUG_SNAPSHOT and save output to data/debug_snapshot.txt."
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
        func_full_reset
        ;;
    task-reset)
        func_task_reset
        ;;
    snapshot)
        func_snapshot
        ;;
    debug-snapshot)
        func_debug_snapshot
        ;;
    *)
        echo "Error: Unknown command '$1'."
        usage
        exit 1
        ;;
esac