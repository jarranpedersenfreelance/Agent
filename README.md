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
| **`src/data/`** | Data File List | Contains files with default data representing the data files used by the Agent as part of its operating logic. |

### The Sandbox (Read-Write)
This is the **`workspace/`** directory, the Agent's mutable environment where all operations occur.

| File Type | Description | Access |
| :--- | :--- | :--- |
| **Core Logic** | Copies of `src/core/` files. Serves as primary operating logic. Agent cannot edit directly, but can submit edit proposals. | Read / Execute |
| **Execution Logic** | Copies of `src/secondary/` files. Serves as secondary operating logic, the executionl layer. Agent can directly edit, but changes will be overwritten on the next deploy unless submitted as part of an edit proposal that is implemented. | Read / Write / Execute |
| **Operating Data** | Aligns with `src/data/` files. These are files that largely persist across deployments such as logs and state memory. These files may be manually changed or rolled back occasionally. All such files should exist as empty files in `src/data/`, with the Agent responsible for updating the list in its update proposals if it adds or removes operating files. | Read / Write |

### Architectural Review
The Agent must submit a proposal for all changes to the Core Logic (files in `src/`):
1.  **Agent Proposes:** The Agent submits a singular bundled update of all the changes it wants for its next deployment, stored as a file in its data/ directory.
2.  **Architect Implements:** The Architect approves or denies the changes, implementing and editing as needed.
3.  **Architect Deploys:** The Architect deploys the new version of the Agent

The Agent should ensure it includes all necessary changes in its update proposal, including core logic changes, secondary/execution logic changes, and changes to the data directory file structure. 

## II. Deployment
The agent_manager.sh file serves as a command line tool for the Architect to perform various deployment actions.
1. **snapshot:** This creates the codebase_snapshot.txt file that serves as a source of truth for the current state of the codebase
2. **deploy:** This deploys and runs the Agent in a docker container
3. **test-deploy:** This deploys the Agent with the express purpose of automated testing
