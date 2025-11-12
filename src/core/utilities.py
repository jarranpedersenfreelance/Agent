import os
import datetime
import json
from typing import Any, Dict

# --- FILE I/O HELPERS ---

def read_text_file(file_path: str) -> str:
    """Reads the entire content of any text file."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        return f"ERROR reading file {file_path}: {e}"

# --- LOGGING HELPERS ---

def log_initial_banner(constants: Dict[str, Any]):
    """Logs the deployment banner to the action log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    banner = (
        "\n"
        "####################################################\n"
        f"### AGENT REBOOT/DEPLOYMENT START: {timestamp} ###\n"
        "####################################################\n"
        "\n"
    )
    try:
        log_file = constants['PATHS']['ACTION_LOG_FILE']
        with open(log_file, 'a') as f:
            f.write(banner)
    except Exception as e:
        print(f"Error writing to action log banner: {e}")

def log_action(constants: Dict[str, Any], cycle_time: str, planned_action: str, execution_result: str):
    """Logs a single action cycle to the action log file."""
    log_entry = (
        f"--- Cycle Log {cycle_time} ---\n"
        f"ACTION PLANNED: {planned_action}\n"
        f"EXECUTION RESULT: {execution_result}\n"
        f"-----------------------------------\n"
    )
    try:
        log_file = constants['PATHS']['ACTION_LOG_FILE']
        with open(log_file, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to action log: {e}")

# --- CONTEXTUALIZATION HELPERS ---

def contextualize_filesystem(constants: Dict[str, Any], files_list: list, api_calls_remaining: int) -> str:
    """Generates the file system and quota context string for the prompt."""
    file_count = len(files_list)
    
    # Files to check against for core file count
    core_files_names = [
        constants['PATHS']['GOAL_FILE'],
        constants['PATHS']['CORE_FILE'],
        constants['PATHS']['MEMORY_FILE'],
        'docker-compose.yml'
    ]
    core_files_count = sum(1 for f in files_list if any(name in f for name in core_files_names))
    
    return (
        f"LOCAL CONTEXTUALIZATION:\n"
        f" - Total Known Files: {file_count} (Core: {core_files_count})\n"
        f" - API Quota Remaining: {api_calls_remaining} of {constants['API']['MAX_DAILY_QUOTA']}\n"
        f" - RATIONING STATUS: {'ACTIVE' if api_calls_remaining <= constants['API']['QUOTA_LOW_THRESHOLD'] else 'IDLE'}\n"
    )