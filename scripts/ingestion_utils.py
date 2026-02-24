#!/usr/bin/env python3
"""
Ingestion utilities - wrapper functions for file operations.

This module provides utility functions used by the ingestion pipeline.
These are thin wrappers around epstein.file_organizer functionality.
"""

from pathlib import Path
from typing import Any

from epstein.file_organizer import FileOrganizer


def detect_file_type(file_path: str | Path) -> str:
    """Detect file type from extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        File type as string (e.g., 'pdf', 'zip', 'image')
    """
    organizer = FileOrganizer(base_dir=Path("/tmp"))
    file_type = organizer.detect_file_type(Path(file_path))
    return file_type.value if hasattr(file_type, 'value') else str(file_type)


def generate_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str:
    """Generate hash of file contents.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)
        
    Returns:
        Hex digest of file hash
    """
    import hashlib
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_file_metadata(file_path: str | Path) -> dict[str, Any]:
    """Get file metadata.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file metadata
    """
    import os
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "extension": path.suffix,
    }


def safe_filename(filename: str) -> str:
    """Convert filename to safe version.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename with invalid characters removed
    """
    import re
    
    # Remove invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove leading/trailing whitespace
    safe = safe.strip()
    # Ensure not empty
    if not safe:
        safe = "unnamed"
    return safe
