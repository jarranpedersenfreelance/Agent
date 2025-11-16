import difflib
from typing import Any, Dict, List
from core.utilities import write_file
from core.execution.toolbox import Tool

class DiffTool(Tool):
    """
    A tool to generate a unified diff between original and new file contents.
    """

    def run(self, args: Dict[str, Any]) -> str:
        """
        Generates a unified diff string for multiple files.

        Args:
            args (Dict[str, Any]): A dictionary containing:
                - "files_to_diff": Dict[str, Dict[str, str]]
                    A dictionary where keys are file paths (e.g., "secondary/my_file.py")
                    and values are dictionaries with "original_content" and "new_content" keys.
                    An empty string for content implies the file did not exist (for original_content)
                    or was deleted (for new_content).
                - "diff_file": str
                    An optional file path to create diff files other than update_request.patch
        
        Returns:
            str: diff file contents
        """
        files_to_diff: Dict[str, Dict[str, str]] = args.get("files_to_diff", {})

        all_diffs: List[str] = []

        for file_path, contents in files_to_diff.items():
            original_content_lines = contents.get("original_content", "").splitlines(keepends=True)
            new_content_lines = contents.get("new_content", "").splitlines(keepends=True)

            diff = difflib.unified_diff(
                original_content_lines,
                new_content_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}"
            )
            all_diffs.extend(list(diff))
        file_content = "".join(all_diffs)

        file_path: str = args.get("file_path", "")
        if (file_path):
            write_file(file_path, file_content)
        else:
            write_file(self.constants['FILE_PATHS']['PATCH_FILE'], file_content)

        return file_content
