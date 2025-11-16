#!/bin/bash

# --- CONFIGURATION ---
SERVICE_NAME="agent"
CONTAINER_NAME="agent_container"
SNAPSHOT_FILE="codebase_snapshot.txt"
MEMORY_FILE="workspace/data/memory.json"
TODO_FILE="to_do.txt"
PATCH_FILE="workspace/data/update_request.patch"
MAX_SNAPSHOT_SIZE=3000000 # ~3 MB (can increase up to 10)
SNAPSHOT_EXCLUSIONS='workspace|*.git|.env|.DS_Store|to_do.txt'

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

function func_cleanup_dangling_images() {
    # Removes dangling images (those tagged as <none>) to prevent disk space issues
    echo "Cleaning up dangling Docker images..."
    docker image prune --force --filter "dangling=true" 2>/dev/null || true
}

# --- CORE DEPLOYMENT LOGIC ---

function func_pre_deploy() {
    echo "Ensuring clean slate..."

    # Cleanup Logs
    func_cleanup_output_files

    # Container Management (Stop/Remove Old Instance)
    docker-compose stop "$SERVICE_NAME" 2>/dev/null || true
    docker-compose rm -f "$SERVICE_NAME" 2>/dev/null || true

    # Workspace Cleanup (Code Directories)
    chmod -R u+w workspace/core 2>/dev/null || true
    chmod -R u+w workspace/secondary 2>/dev/null || true
    rm -rf workspace/core/*
    rm -rf workspace/secondary/*
    
    # Copy Code and Initial State/Data & Set Permissions
    func_copy_initial_files
}

function func_deploy() {
    echo "--- DEPLOYMENT START: $(date) ---"
    echo ""

    # Clean and Re-Copy Files
    func_pre_deploy

    # Build and Start
    echo "Building and starting the '$SERVICE_NAME' container..."
    docker-compose up -d --build "$SERVICE_NAME"

    # Clean up dangling images created by the build process
    func_cleanup_dangling_images

    echo ""
    echo "--- DEPLOYMENT END: $(date) ---"
}

function func_todo_deploy() {
    echo "--- DEPLOYMENT START: $(date) ---"
    echo ""

    # Clean and Re-Copy Files
    func_pre_deploy
    
    # copy to_do.txt contents to memory.json ToDo field as List[str]
    echo "Injecting ToDo list from $TODO_FILE into $MEMORY_FILE..."
    
    if [ -f "$TODO_FILE" ]; then
        # Check for jq
        if ! command -v jq &> /dev/null; then
            echo "ERROR: 'jq' command is required for JSON manipulation but was not found. Skipping."
            echo ""
            echo "--- DEPLOYMENT END: $(date) ---"
            return 1
        fi
        
        # read list from file as json List[str]
        TODO_LIST_JSON=$(jq -R -s 'split("\n") | map(select(length > 0)) | map(select(test("^\\s*$") | not))' "$TODO_FILE")
        
        # check if memory.json exists
        if [ ! -f "$MEMORY_FILE" ]; then
            echo "ERROR: $MEMORY_FILE is missing after deployment. Cannot inject ToDo list."
            echo ""
            echo "--- DEPLOYMENT END: $(date) ---"
            return 1
        fi

        # use jq to read memory.json, set the 'todo' field, and write back.
        jq --argjson todo_array "$TODO_LIST_JSON" '. + {todo: $todo_array}' "$MEMORY_FILE" > temp.json
        
        if [ $? -eq 0 ]; then
            mv temp.json "$MEMORY_FILE"
            echo "Successfully injected $(echo "$TODO_LIST_JSON" | jq 'length') items into 'todo' field."
        else
            echo "ERROR: Failed to process $MEMORY_FILE with jq. Check memory.json structure."
            rm -f temp.json
        fi
        
    else
        echo "ERROR: $TODO_FILE not found. Skipping ToDo list injection."
        echo ""
        echo "--- DEPLOYMENT END: $(date) ---"
        return 1
    fi

    # Build and Start
    echo "Building and starting the '$SERVICE_NAME' container..."
    docker-compose up -d --build "$SERVICE_NAME"

    # Clean up dangling images created by the build process
    func_cleanup_dangling_images
    
    echo ""
    echo "--- DEPLOYMENT END: $(date) ---"
}

function func_snapshot() {
    echo "--- SNAPSHOT GENERATION START: $(date) ---"
    rm -f "$SNAPSHOT_FILE"

    echo "Generating Directory Structure..."
    {
        echo "=================================================="
        echo "## PROJECT DIRECTORY STRUCTURE"
        echo "=================================================="
        tree -a -F -I "$SNAPSHOT_EXCLUSIONS" --noreport 2>/dev/null || (
            echo "Warning: 'tree' command not found. Falling back to 'find/ls'."
            find . -not -path "./workspace/*" -not -path "./.git/*" -not -name "$SNAPSHOT_FILE" -not -name ".env" -not -name ".DS_Store" | sort
        )
        echo ""
    } > "$SNAPSHOT_FILE"

    echo "Compiling File Contents..."
    echo "--- FILE CONTENTS START ---" >> "$SNAPSHOT_FILE"

    find . -type f -not -path "./workspace/*" -not -name "$SNAPSHOT_FILE" -not -path "./.git/*" -not -name ".env" -not -name ".DS_Store" | while IFS= read -r FILE; do
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

function func_clean() {
    echo "Emptying workspace directory..."
    chmod -R u+w workspace/ 2>/dev/null || true
    rm -rf workspace/*
}

function func_apply_patch() {
    # Use the first argument as the patch file, or default to $PATCH_FILE
    local patch_file="${1:-$PATCH_FILE}"

    echo "--- APPLYING PATCH: $patch_file ---"

    # Check for the 'patch' command
    if ! command -v patch &> /dev/null; then
        echo "ERROR: 'patch' command is required but was not found."
        echo "Please install 'patch' (e.g., 'sudo apt-get install patch') and try again."
        return 1
    fi

    # Check if the patch file exists
    if [ ! -f "$patch_file" ]; then
        echo "ERROR: Patch file not found at '$patch_file'."
        return 1
    fi

    # Check if the src directory exists
    if [ ! -d "src" ]; then
        echo "ERROR: 'src/' directory not found. Are you in the project root?"
        return 1
    fi

    echo "Applying $patch_file to src/ directory..."
    # -d src: Apply patch relative to the 'src' directory
    # -p1: Strip the 'a/' and 'b/' prefix (1 directory level) from paths in the patch file
    patch -d src -p1 < "$patch_file"

    if [ $? -eq 0 ]; then
        echo "Patch applied successfully."
    else
        echo "WARNING: 'patch' command finished with errors."
        echo "The patch may have been partially applied or rejected."
        echo "Please review the output and your 'src/' files."
    fi
    echo "--- PATCH COMPLETE ---"
}

function usage() {
    echo "Usage: ./agent_manager.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  deploy             : Deploy and start the agent."
    echo "  todo-deploy        : Update ToDo list in agent memory, then deploy and start the agent."
    echo "  apply-patch [file] : Apply a .patch file to the 'src/' directory. Uses $PATCH_FILE by default."
    echo "  clean              : Clear the workspace directory."
    echo "  logs               : Display the most recent logs from the agent container."
    echo "  snapshot           : Generate the codebase_snapshot.txt file for context upload."
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
    todo-deploy)
        func_todo_deploy
        ;;
    clean)
        func_clean
        ;;
    logs)
        func_logs
        ;;
    snapshot)
        func_snapshot
        ;;
    patch)
        func_apply_patch "$2" # Pass the second argument (optional patch file)
        ;;
    *)
        usage
        exit 1
        ;;
esac