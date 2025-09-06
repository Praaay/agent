"""File utility functions for the DevSage debugging system."""

import os
import aiofiles
from pathlib import Path
from typing import Optional, List, Dict, Any


async def read_file_content(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """Read file content asynchronously."""
    try:
        async with aiofiles.open(file_path, mode="r", encoding=encoding) as file:
            return await file.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def read_file_content_sync(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """Read file content synchronously."""
    try:
        with open(file_path, mode="r", encoding=encoding) as file:
            return file.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def get_file_extension(file_path: str) -> str:
    """Get file extension from path."""
    return Path(file_path).suffix.lower()


def get_file_language(file_path: str) -> str:
    """Determine programming language from file extension."""
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".sh": "bash",
        ".ps1": "powershell",
    }
    
    extension = get_file_extension(file_path)
    return extension_map.get(extension, "unknown")


def get_surrounding_lines(file_path: str, line_number: int, context_lines: int = 5) -> Optional[str]:
    """Get surrounding lines of code around a specific line number."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            
        start_line = max(0, line_number - context_lines - 1)
        end_line = min(len(lines), line_number + context_lines)
        
        surrounding_lines = lines[start_line:end_line]
        return "".join(surrounding_lines)
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error reading surrounding lines from {file_path}: {e}")
        return None


def find_project_root(start_path: str) -> Optional[str]:
    """Find the project root directory by looking for common project files."""
    current_path = Path(start_path).resolve()
    
    # Common project root indicators
    indicators = [
        ".git",
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        "setup.py",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "Makefile",
        "CMakeLists.txt",
    ]
    
    while current_path != current_path.parent:
        for indicator in indicators:
            if (current_path / indicator).exists():
                return str(current_path)
        current_path = current_path.parent
    
    return None


def get_project_structure(project_path: str, max_depth: int = 3) -> Dict[str, Any]:
    """Get project structure as a dictionary."""
    project_path = Path(project_path)
    structure = {"name": project_path.name, "type": "directory", "children": []}
    
    def build_tree(path: Path, depth: int) -> Dict[str, Any]:
        if depth > max_depth:
            return {"name": path.name, "type": "file", "truncated": True}
        
        if path.is_file():
            return {
                "name": path.name,
                "type": "file",
                "language": get_file_language(str(path)),
                "size": path.stat().st_size,
            }
        
        children = []
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith(".") and item.name != ".git":
                    continue
                children.append(build_tree(item, depth + 1))
        except PermissionError:
            pass
        
        return {
            "name": path.name,
            "type": "directory",
            "children": children,
        }
    
    structure["children"] = build_tree(project_path, 0)["children"]
    return structure


def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary."""
    try:
        with open(file_path, "rb") as file:
            chunk = file.read(1024)
            return b"\x00" in chunk
    except (FileNotFoundError, PermissionError):
        return False 