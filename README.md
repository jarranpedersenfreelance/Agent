# The Agent: A Self-Evolving Assistant

The Agent is a self-optimizing, containerized AI designed to execute complex tasks and continuously evolve its own operational logic.

## I. System Architecture & Component Roles

The system enforces a strict separation between read-only source and the execution environment.

### Framework and Source Code (Read-Only)
These files are tracked by version control and are mounted **read-only** into the container. The Agent cannot modify these files.

| Directory/Level | Component Type | Purpose |
| :--- | :--- | :--- |
| **Base Level** | Framework | Contains foundational files (`README.md`, `goal.txt`, `deploy`, etc.). |
| **`src/core/`** | Core Logic | Contains the primary module managing the Agent's consciousness, state, and reasoning loop. |
| **`src/secondary/`** | Execution Logic | Contains modular tools (e.g., action parsing, file handling, command execution) that abstract the physical layer. |
| **`src/data/`** | Data File List | Contains empty files representing the data files used by the Agent as part of its operating logic. |

### The Sandbox (Read-Write)
This is the **`workspace/`** directory, the Agent's mutable environment where all operations occur.

| File Type | Description | Access |
| :--- | :--- | :--- |
| **Core Logic** | Copies of `src/core/` files. Serves as primary operating logic. Agent cannot edit directly, but can submit edit proposals. | Read / Execute |
| **Execution Logic** | Copies of `src/secondary/` files. Serves as secondary operating logic, the executionl layer. Agent can directly edit, but changes will be overwritten on the next deploy unless submitted as part of an edit proposal that is implemented. | Read / Write / Execute |
| **Operating Data** | Aligns with `src/data/` files. These are files that largely persist across deployments such as logs and state memory. These files may be manually changed or rolled back occasionally. All such files should exist as empty files in `src/data/`, with the Agent responsible for updating the list in its update proposals if it adds or removes operating files. | Read / Write |
| **Temp** | These are files that the Agent downloads or creates for temporary use. They will be regularly deleted and not guaranteed to persist across deployments. | Read / Write / Execute |

## II. Deployment & Update Protocol (Architectural Review)

### Initial Deployment & Code Updates

To start the Agent or deploy a code update after making changes to the `src/` files, execute the deploy script:

./deploy

This script will:
1. Copy all necessary Framework/Core Logic files from the source directories into the `workspace/`.
2. Rebuild and restart the Docker container with the new code.

### Core Logic Updates (Architectural Review)
The Agent must submit a proposal for all changes to the Core Logic (files in `src/`):
1.  **Agent Proposes:** The Agent logs an **ACTION PROPOSAL** targeting the file in the workspace (e.g., `core/agent_core.py`).
2.  **Architect Implements:** The Architect manually copies the approved changes into the corresponding file in the local **`src/` directory**, editing if needed.
3.  **Architect Deploys:** The Architect executes `./deploy` to synchronize the new source code to the Agent's environment.

The Agent should ensure it includes all necessary changes in its update proposal, including core logic changes, secondary/execution logic changes, and changes to the data directory file structure. 