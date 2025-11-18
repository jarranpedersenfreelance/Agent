import difflib
import os
from typing import Any, Dict, List
from core.utilities import write_file, read_file
from core.execution.toolbox import Tool

class DiffTool(Tool):
    """
    A tool to generate a unified diff by comparing workspace files
    against their original versions in the /app/src/ directory.
    """

    def run(self, args: Dict[str, Any] = {}) -> str:
        """
        Generates a unified diff string for multiple files and writes it to a file.

        Args:
            args (Dict[str, Any]): A dictionary containing:
                - "files": List[str]
                    A list of file paths relative to the workspace root
                    (e.g., "data/my_first_file.txt").
                - "output_file_path": str
                    An optional file path to write the diff contents to, overriding the
                    default patch file path from constants.
        Returns:
            str: The generated diff file contents.
        """
        files_to_diff: List[str] = args.get("files", [])
        if not files_to_diff:
            self._logger.log_warning("DiffTool ran but 'files' list was empty.")
            return ""

        all_diffs: List[str] = []
        
        # The original read-only code is at /app/src/
        src_dir = "/app/src"
        workspace_dir = "."

        for file_path in files_to_diff:
            # Get "b/" version (the new/modified file in the workspace)
            new_file_full_path = os.path.join(workspace_dir, file_path)
            new_content = ""
            if os.path.exists(new_file_full_path):
                new_content = read_file(new_file_full_path)
            
            new_content_lines = new_content.splitlines(keepends=True)

            # Get "a/" version (the original file from src)
            original_file_full_path = os.path.join(src_dir, file_path)
            original_content = ""
            if os.path.exists(original_file_full_path):
                original_content = read_file(original_file_full_path)

            original_content_lines = original_content.splitlines(keepends=True)

            # Generate the diff
            diff = difflib.unified_diff(
                original_content_lines,
                new_content_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}"
            )
            all_diffs.extend(list(diff))
            
        file_content = "".join(all_diffs)
        
        # Write the patch file
        output_file_path: str = args.get("output_file_path", "")
        
        patch_path: str
        if output_file_path:
            patch_path = output_file_path
        else:
            patch_path = self._constants['FILE_PATHS']['PATCH_FILE']
            
        write_file(patch_path, file_content)
        self._memory.fill_file_contents(patch_path, file_content)
        
        self._logger.log_info(f"DiffTool generated patch for {len(files_to_diff)} files.")
        return file_content