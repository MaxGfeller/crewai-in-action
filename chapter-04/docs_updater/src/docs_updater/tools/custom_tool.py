from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import shutil
import os


class FileCopyToolInput(BaseModel):
    """Input schema for FileCopyTool."""
    source_path: str = Field(..., description="The full path to the source file to copy")
    destination_path: str = Field(..., description="The full path where the file should be copied to")


class FileCopyTool(BaseTool):
    name: str = "File Copy Tool"
    description: str = (
        "Copies a file from one location to another. Use this to copy screenshot images "
        "from temporary directories to the documentation folder. Works with any file type "
        "including images (PNG, JPG, etc.)."
    )
    args_schema: Type[BaseModel] = FileCopyToolInput

    def _run(self, source_path: str, destination_path: str) -> str:
        try:
            # Ensure the destination directory exists
            dest_dir = os.path.dirname(destination_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            # Copy the file
            shutil.copy2(source_path, destination_path)
            return f"Successfully copied file from {source_path} to {destination_path}"
        except FileNotFoundError:
            return f"Error: Source file not found at {source_path}"
        except PermissionError:
            return f"Error: Permission denied when copying to {destination_path}"
        except Exception as e:
            return f"Error copying file: {str(e)}"
