"""
Scoped file tools that restrict file operations to a specific base directory.
All paths exposed to the agent are relative paths within the base directory.
"""

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import shutil

class PathSecurityError(Exception):
    """Raised when a path traversal attack is detected."""
    pass


def validate_and_resolve_path(relative_path: str, base_directory: str) -> str:
    """
    Validate that a relative path stays within the base directory.
    Returns the absolute path if valid, raises PathSecurityError if not.

    Security measures:
    1. Normalize the relative path (remove .., ., etc.)
    2. Join with base directory
    3. Canonicalize using realpath
    4. Verify the result starts with the base directory
    """
    # Normalize the base directory to absolute path
    base_abs = os.path.realpath(os.path.abspath(base_directory))

    # Clean the relative path - remove leading slashes to prevent absolute path injection
    clean_relative = relative_path.lstrip('/')

    # Join and canonicalize
    joined_path = os.path.join(base_abs, clean_relative)
    canonical_path = os.path.realpath(joined_path)

    # Security check: ensure the canonical path is within the base directory
    if not canonical_path.startswith(base_abs + os.sep) and canonical_path != base_abs:
        raise PathSecurityError(
            f"Path '{relative_path}' resolves outside the allowed directory. "
            "Path traversal is not permitted."
        )

    return canonical_path


def get_relative_path(absolute_path: str, base_directory: str) -> str:
    """Convert an absolute path to a relative path from the base directory."""
    base_abs = os.path.realpath(os.path.abspath(base_directory))
    return os.path.relpath(absolute_path, base_abs)


# ============== Input Schemas ==============

class DirectoryListInput(BaseModel):
    """Input schema for directory listing."""
    directory: str = Field(
        default=".",
        description="Relative path to the directory to list (e.g., 'images' or 'api-reference'). Use '.' for the root docs directory."
    )


class FileReadInput(BaseModel):
    """Input schema for reading files."""
    file_path: str = Field(
        ...,
        description="Relative path to the file to read (e.g., 'introduction.mdx' or 'api-reference/overview.mdx')"
    )


class FileWriteInput(BaseModel):
    """Input schema for writing files."""
    file_path: str = Field(
        ...,
        description="Relative path where the file should be written (e.g., 'getting-started.mdx')"
    )
    content: str = Field(
        ...,
        description="The content to write to the file"
    )


class FileCopyInput(BaseModel):
    """Input schema for copying files."""
    source_path: str = Field(
        ...,
        description="Source path - can be absolute (for external files like screenshots) or relative (for files within docs)"
    )
    destination_path: str = Field(
        ...,
        description="Relative path within the docs directory (e.g., 'images/dashboard.png')"
    )


# ============== Tool Implementations ==============

class ScopedDirectoryListTool(BaseTool):
    """Lists directory contents using relative paths only."""

    name: str = "list_docs_directory"
    description: str = """List the contents of a directory within the documentation folder.
Use relative paths like 'images', 'api-reference', or '.' for the root.
Returns a list of files and subdirectories with their relative paths."""
    args_schema: Type[BaseModel] = DirectoryListInput

    base_directory: str = ""

    def _run(self, directory: str = ".") -> str:
        try:
            abs_path = validate_and_resolve_path(directory, self.base_directory)

            if not os.path.isdir(abs_path):
                return f"Error: '{directory}' is not a directory"

            entries = []
            for entry in sorted(os.listdir(abs_path)):
                entry_path = os.path.join(abs_path, entry)
                rel_path = get_relative_path(entry_path, self.base_directory)
                entry_type = "[DIR]" if os.path.isdir(entry_path) else "[FILE]"
                entries.append(f"{entry_type} {rel_path}")

            if not entries:
                return f"Directory '{directory}' is empty"

            return f"Contents of '{directory}':\n" + "\n".join(entries)

        except PathSecurityError as e:
            return f"Security Error: {str(e)}"
        except Exception as e:
            return f"Error listing directory: {str(e)}"


class ScopedFileReadTool(BaseTool):
    """Reads files using relative paths only."""

    name: str = "read_docs_file"
    description: str = """Read a file from the documentation folder.
Use relative paths like 'introduction.mdx' or 'api-reference/overview.mdx'.
Returns the file contents as text."""
    args_schema: Type[BaseModel] = FileReadInput

    base_directory: str = ""

    def _run(self, file_path: str) -> str:
        try:
            abs_path = validate_and_resolve_path(file_path, self.base_directory)

            if not os.path.isfile(abs_path):
                return f"Error: File '{file_path}' not found"

            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return f"Contents of '{file_path}':\n\n{content}"

        except PathSecurityError as e:
            return f"Security Error: {str(e)}"
        except UnicodeDecodeError:
            return f"Error: '{file_path}' is a binary file and cannot be read as text"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class ScopedFileWriteTool(BaseTool):
    """Writes files using relative paths only."""

    name: str = "write_docs_file"
    description: str = """Write content to a file in the documentation folder.
Use relative paths like 'getting-started.mdx' or 'guides/new-guide.mdx'.
Creates parent directories if they don't exist. Overwrites existing files."""
    args_schema: Type[BaseModel] = FileWriteInput

    base_directory: str = ""

    def _run(self, file_path: str, content: str) -> str:
        try:
            abs_path = validate_and_resolve_path(file_path, self.base_directory)

            # Create parent directories if needed
            parent_dir = os.path.dirname(abs_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)

            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"Successfully wrote to '{file_path}'"

        except PathSecurityError as e:
            return f"Security Error: {str(e)}"
        except Exception as e:
            return f"Error writing file: {str(e)}"


class ScopedFileCopyTool(BaseTool):
    """Copies files into the docs directory."""

    name: str = "copy_to_docs"
    description: str = """Copy a file to the documentation folder.
Source can be an absolute path (for external files like screenshots from /tmp).
Destination must be a relative path within the docs folder (e.g., 'images/dashboard.png').
Creates parent directories if they don't exist."""
    args_schema: Type[BaseModel] = FileCopyInput

    base_directory: str = ""

    def _run(self, source_path: str, destination_path: str) -> str:
        try:
            # Destination must be within base directory
            dest_abs = validate_and_resolve_path(destination_path, self.base_directory)

            # Source can be absolute (external) or relative (internal)
            if os.path.isabs(source_path):
                source_abs = source_path
            else:
                source_abs = validate_and_resolve_path(source_path, self.base_directory)

            if not os.path.isfile(source_abs):
                return f"Error: Source file not found at '{source_path}'"

            # Create parent directories if needed
            parent_dir = os.path.dirname(dest_abs)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)

            shutil.copy2(source_abs, dest_abs)

            return f"Successfully copied to '{destination_path}'"

        except PathSecurityError as e:
            return f"Security Error: {str(e)}"
        except Exception as e:
            return f"Error copying file: {str(e)}"


# ============== Factory Function ==============

def get_scoped_file_tools(base_directory: str) -> list:
    """
    Create a set of file tools scoped to the given base directory.

    Args:
        base_directory: Absolute path to the docs directory

    Returns:
        List of tool instances configured for the base directory
    """
    if not os.path.isdir(base_directory):
        raise ValueError(f"Base directory does not exist: {base_directory}")

    base_abs = os.path.realpath(base_directory)

    tools = []
    for ToolClass in [ScopedDirectoryListTool, ScopedFileReadTool,
                      ScopedFileWriteTool]:
        tool = ToolClass()
        tool.base_directory = base_abs
        tools.append(tool)

    return tools


def get_copy_tool(base_directory: str) -> ScopedFileCopyTool:
    """
    Get just the copy tool, scoped to the given base directory.
    Useful for the screenshotter agent that only needs to copy files.
    """
    if not os.path.isdir(base_directory):
        raise ValueError(f"Base directory does not exist: {base_directory}")

    tool = ScopedFileCopyTool()
    tool.base_directory = os.path.realpath(base_directory)
    return tool
