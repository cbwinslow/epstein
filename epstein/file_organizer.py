#!/usr/bin/env python3
"""
File Organization and Management System
Handles unzipping, naming conventions, deduplication, and file storage organization.

Author: Epstein Project Team
Date: 2026-02-13
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Supported file types"""
    PDF = "pdf"
    ZIP = "zip"
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    AUDIO = "audio"
    UNKNOWN = "unknown"


class FileCategory(Enum):
    """File categories for organization"""
    COURT_RECORDS = "court_records"
    DOJ_DISCLOSURES = "doj_disclosures"
    FBI_RECORDS = "fbi_records"
    HOUSE_OVERSIGHT = "house_oversight"
    EMAILS = "emails"
    IMAGES = "images"
    VIDEOS = "videos"
    TRANSCRIPTS = "transcripts"
    OTHER = "other"


@dataclass
class FileMetadata:
    """Metadata for organized files"""
    original_path: Path
    organized_path: Path
    file_type: FileType
    category: FileCategory
    hash_sha256: str
    size_bytes: int
    created_at: datetime
    source: str
    dataset_number: int | None = None
    original_filename: str = ""
    normalized_filename: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "original_path": str(self.original_path),
            "organized_path": str(self.organized_path),
            "file_type": self.file_type.value,
            "category": self.category.value,
            "hash_sha256": self.hash_sha256,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "dataset_number": self.dataset_number,
            "original_filename": self.original_filename,
            "normalized_filename": self.normalized_filename,
            "metadata": self.metadata,
        }


class FileOrganizer:
    """
    Comprehensive file organization system with:
    - Automatic unzipping with validation
    - Consistent naming conventions
    - Deduplication by hash
    - Category-based organization
    - Metadata tracking
    - Safe file operations
    """

    # File type extensions mapping
    FILE_EXTENSIONS = {
        FileType.PDF: {".pdf"},
        FileType.ZIP: {".zip", ".7z", ".tar", ".gz", ".bz2"},
        FileType.IMAGE: {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"},
        FileType.VIDEO: {".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"},
        FileType.TEXT: {".txt", ".doc", ".docx", ".rtf", ".odt"},
        FileType.AUDIO: {".mp3", ".wav", ".ogg", ".m4a", ".flac"},
    }

    # Naming pattern for different sources
    NAMING_PATTERNS = {
        "doj_disclosures": "DOJ_DS{dataset:02d}_{date}_{index:04d}_{name}",
        "fbi_vault": "FBI_Part{part:02d}_{date}_{index:04d}_{name}",
        "house_oversight": "HOUSE_{release}_{date}_{index:04d}_{name}",
        "default": "{source}_{date}_{index:04d}_{name}",
    }

    def __init__(
        self,
        base_dir: Path,
        organized_dir: Path | None = None,
        dedup_enabled: bool = True,
        auto_extract_zips: bool = True
    ):
        """
        Initialize file organizer

        Args:
            base_dir: Base directory for raw files
            organized_dir: Directory for organized files (defaults to base_dir/organized)
            dedup_enabled: Enable deduplication by hash
            auto_extract_zips: Automatically extract ZIP files
        """
        self.base_dir = Path(base_dir)
        self.organized_dir = Path(organized_dir) if organized_dir else self.base_dir / "organized"
        self.dedup_enabled = dedup_enabled
        self.auto_extract_zips = auto_extract_zips

        # Create directory structure
        self._create_directory_structure()

        # Deduplication tracking
        self.hash_registry: dict[str, Path] = {}
        self.hash_registry_file = self.organized_dir / "hash_registry.json"
        self._load_hash_registry()

        # Metadata tracking
        self.metadata_file = self.organized_dir / "file_metadata.jsonl"

        # File counter for unique naming
        self.file_counters: dict[str, int] = {}

        logger.info(f"File organizer initialized: base={base_dir}, organized={self.organized_dir}")

    def _create_directory_structure(self) -> None:
        """Create organized directory structure"""
        self.organized_dir.mkdir(parents=True, exist_ok=True)

        # Create category subdirectories
        for category in FileCategory:
            category_dir = self.organized_dir / category.value
            category_dir.mkdir(exist_ok=True)

        # Create special directories
        (self.organized_dir / "duplicates").mkdir(exist_ok=True)
        (self.organized_dir / "extracted").mkdir(exist_ok=True)
        (self.organized_dir / "failed").mkdir(exist_ok=True)

    def _load_hash_registry(self) -> None:
        """Load hash registry from disk"""
        if self.hash_registry_file.exists():
            try:
                with open(self.hash_registry_file) as f:
                    data = json.load(f)
                    self.hash_registry = {k: Path(v) for k, v in data.items()}
                logger.info(f"Loaded {len(self.hash_registry)} entries from hash registry")
            except Exception as e:
                logger.error(f"Failed to load hash registry: {e}")
                self.hash_registry = {}

    def _save_hash_registry(self) -> None:
        """Save hash registry to disk"""
        try:
            data = {k: str(v) for k, v in self.hash_registry.items()}
            with open(self.hash_registry_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save hash registry: {e}")

    def detect_file_type(self, file_path: Path) -> FileType:
        """Detect file type based on extension"""
        suffix = file_path.suffix.lower()

        for file_type, extensions in self.FILE_EXTENSIONS.items():
            if suffix in extensions:
                return file_type

        return FileType.UNKNOWN

    def categorize_file(self, file_path: Path, source: str = "") -> FileCategory:
        """
        Categorize file based on name, source, and content

        Args:
            file_path: Path to file
            source: Source identifier (doj_disclosures, fbi_vault, etc.)

        Returns:
            FileCategory enum value
        """
        filename = file_path.name.lower()

        # Source-based categorization
        if "doj" in source.lower():
            return FileCategory.DOJ_DISCLOSURES
        elif "fbi" in source.lower():
            return FileCategory.FBI_RECORDS
        elif "house" in source.lower():
            return FileCategory.HOUSE_OVERSIGHT

        # Content-based categorization
        if "court" in filename or "docket" in filename:
            return FileCategory.COURT_RECORDS
        elif "email" in filename or "message" in filename:
            return FileCategory.EMAILS
        elif self.detect_file_type(file_path) == FileType.IMAGE:
            return FileCategory.IMAGES
        elif self.detect_file_type(file_path) == FileType.VIDEO:
            return FileCategory.VIDEOS
        elif "transcript" in filename or "deposition" in filename:
            return FileCategory.TRANSCRIPTS

        return FileCategory.OTHER

    def normalize_filename(
        self,
        original_filename: str,
        source: str = "default",
        dataset_number: int | None = None,
        index: int = 0
    ) -> str:
        """
        Generate normalized filename following naming conventions

        Args:
            original_filename: Original file name
            source: Source identifier
            dataset_number: Dataset number (for DOJ/FBI)
            index: Sequential index for uniqueness

        Returns:
            Normalized filename
        """
        # Clean original filename
        name = Path(original_filename).stem
        ext = Path(original_filename).suffix

        # Remove special characters and normalize
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '_', name)
        name = name[:50]  # Limit length

        # Get current date
        date_str = datetime.now(UTC).strftime("%Y%m%d")

        # Select naming pattern
        pattern = self.NAMING_PATTERNS.get(source, self.NAMING_PATTERNS["default"])

        # Format filename
        try:
            if source == "doj_disclosures" and dataset_number is not None:
                normalized = pattern.format(
                    dataset=dataset_number,
                    date=date_str,
                    index=index,
                    name=name
                )
            elif source == "fbi_vault" and dataset_number is not None:
                normalized = pattern.format(
                    part=dataset_number,
                    date=date_str,
                    index=index,
                    name=name
                )
            else:
                normalized = pattern.format(
                    source=source.upper(),
                    date=date_str,
                    index=index,
                    name=name
                )
        except Exception as e:
            logger.warning(f"Failed to format filename with pattern: {e}")
            normalized = f"{source}_{date_str}_{index:04d}_{name}"

        return f"{normalized}{ext}"

    def calculate_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate file hash"""
        hasher = hashlib.new(algorithm)

        with open(file_path, "rb") as f:
            while chunk := f.read(8 * 1024 * 1024):
                hasher.update(chunk)

        return hasher.hexdigest()

    def is_duplicate(self, file_hash: str) -> tuple[bool, Path | None]:
        """
        Check if file is a duplicate

        Args:
            file_hash: SHA256 hash of file

        Returns:
            Tuple of (is_duplicate, existing_file_path)
        """
        if not self.dedup_enabled:
            return False, None

        existing_path = self.hash_registry.get(file_hash)

        if existing_path and existing_path.exists():
            return True, existing_path

        return False, None

    def extract_zip(
        self,
        zip_path: Path,
        extract_dir: Path | None = None,
        organize_extracted: bool = True
    ) -> tuple[bool, list[Path], str | None]:
        """
        Extract ZIP file with safety checks

        Args:
            zip_path: Path to ZIP file
            extract_dir: Directory to extract to (defaults to organized_dir/extracted)
            organize_extracted: Whether to organize extracted files

        Returns:
            Tuple of (success, extracted_files, error_message)
        """
        if not zipfile.is_zipfile(zip_path):
            return False, [], "Not a valid ZIP file"

        extract_dir = extract_dir or (self.organized_dir / "extracted" / zip_path.stem)
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Validate ZIP integrity
            with zipfile.ZipFile(zip_path, "r") as zf:
                bad_file = zf.testzip()
                if bad_file:
                    return False, [], f"Corrupt ZIP member: {bad_file}"

                # Extract with Zip Slip protection
                extracted_files = []

                for member in zf.infolist():
                    # Normalize and validate path
                    member_path = extract_dir / member.filename
                    member_path = member_path.resolve()

                    # Check for Zip Slip
                    if not str(member_path).startswith(str(extract_dir.resolve())):
                        logger.warning(f"Blocked Zip Slip attempt: {member.filename}")
                        continue

                    # Skip directories
                    if member.is_dir():
                        member_path.mkdir(parents=True, exist_ok=True)
                        continue

                    # Extract file
                    member_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, open(member_path, "wb") as target:
                        shutil.copyfileobj(source, target)

                    extracted_files.append(member_path)

                logger.info(f"Extracted {len(extracted_files)} files from {zip_path.name}")

                # Organize extracted files if requested
                if organize_extracted:
                    for file_path in extracted_files:
                        self.organize_file(file_path, source=zip_path.stem)

                return True, extracted_files, None

        except Exception as e:
            error_msg = f"ZIP extraction failed: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg

    def organize_file(
        self,
        file_path: Path,
        source: str = "",
        dataset_number: int | None = None,
        force: bool = False
    ) -> tuple[bool, Path | None, str | None]:
        """
        Organize a single file

        Args:
            file_path: Path to file to organize
            source: Source identifier
            dataset_number: Dataset number if applicable
            force: Force organization even if duplicate

        Returns:
            Tuple of (success, organized_path, error_message)
        """
        if not file_path.exists():
            return False, None, f"File not found: {file_path}"

        try:
            # Calculate hash
            file_hash = self.calculate_hash(file_path)

            # Check for duplicates
            is_dup, existing_path = self.is_duplicate(file_hash)

            if is_dup and not force:
                logger.info(f"Duplicate file detected: {file_path.name} (existing: {existing_path})")

                # Move to duplicates folder
                dup_dir = self.organized_dir / "duplicates"
                dup_path = dup_dir / file_path.name

                # Ensure unique name in duplicates
                counter = 1
                while dup_path.exists():
                    dup_path = dup_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                    counter += 1

                shutil.copy2(file_path, dup_path)
                return True, existing_path, "Duplicate (existing file used)"

            # Detect file type and category
            file_type = self.detect_file_type(file_path)
            category = self.categorize_file(file_path, source)

            # Auto-extract ZIP files if enabled
            if file_type == FileType.ZIP and self.auto_extract_zips:
                success, extracted_files, error = self.extract_zip(file_path, organize_extracted=True)
                if not success:
                    logger.warning(f"Failed to extract ZIP {file_path.name}: {error}")

            # Generate normalized filename
            counter_key = f"{source}_{category.value}"
            index = self.file_counters.get(counter_key, 0)
            self.file_counters[counter_key] = index + 1

            normalized_name = self.normalize_filename(
                file_path.name,
                source=source,
                dataset_number=dataset_number,
                index=index
            )

            # Determine organized path
            category_dir = self.organized_dir / category.value
            organized_path = category_dir / normalized_name

            # Ensure unique filename
            counter = 1
            while organized_path.exists():
                stem = Path(normalized_name).stem
                ext = Path(normalized_name).suffix
                organized_path = category_dir / f"{stem}_{counter}{ext}"
                counter += 1

            # Copy file to organized location
            shutil.copy2(file_path, organized_path)

            # Register in hash registry
            self.hash_registry[file_hash] = organized_path
            self._save_hash_registry()

            # Save metadata
            metadata = FileMetadata(
                original_path=file_path,
                organized_path=organized_path,
                file_type=file_type,
                category=category,
                hash_sha256=file_hash,
                size_bytes=organized_path.stat().st_size,
                created_at=datetime.now(UTC),
                source=source,
                dataset_number=dataset_number,
                original_filename=file_path.name,
                normalized_filename=normalized_name,
            )

            self._save_metadata(metadata)

            logger.info(f"Organized: {file_path.name} -> {organized_path.relative_to(self.organized_dir)}")

            return True, organized_path, None

        except Exception as e:
            error_msg = f"Failed to organize file: {str(e)}"
            logger.error(error_msg)

            # Move to failed directory
            failed_dir = self.organized_dir / "failed"
            failed_path = failed_dir / file_path.name

            try:
                shutil.copy2(file_path, failed_path)
            except Exception as copy_error:
                logger.error(f"Failed to copy to failed directory: {copy_error}")

            return False, None, error_msg

    def organize_directory(
        self,
        directory: Path,
        source: str = "",
        recursive: bool = True
    ) -> dict[str, int]:
        """
        Organize all files in a directory

        Args:
            directory: Directory to organize
            source: Source identifier
            recursive: Process subdirectories

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total": 0,
            "success": 0,
            "duplicates": 0,
            "failed": 0,
            "extracted_zips": 0,
        }

        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue

            stats["total"] += 1

            success, organized_path, error = self.organize_file(file_path, source)

            if success:
                if "Duplicate" in (error or ""):
                    stats["duplicates"] += 1
                else:
                    stats["success"] += 1

                # Check if it was a ZIP that got extracted
                if self.detect_file_type(file_path) == FileType.ZIP:
                    stats["extracted_zips"] += 1
            else:
                stats["failed"] += 1

        logger.info(
            f"Directory organization complete: {stats['success']} success, "
            f"{stats['duplicates']} duplicates, {stats['failed']} failed"
        )

        return stats

    def _save_metadata(self, metadata: FileMetadata) -> None:
        """Save file metadata to log"""
        try:
            with open(self.metadata_file, "a") as f:
                f.write(json.dumps(metadata.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def get_statistics(self) -> dict:
        """Get organization statistics"""
        stats = {
            "total_files": 0,
            "by_category": {},
            "by_type": {},
            "total_size_bytes": 0,
            "duplicates_detected": len(self.hash_registry),
        }

        for category in FileCategory:
            category_dir = self.organized_dir / category.value
            if category_dir.exists():
                files = list(category_dir.glob("*"))
                count = len(files)
                size = sum(f.stat().st_size for f in files if f.is_file())

                stats["by_category"][category.value] = {
                    "count": count,
                    "size_bytes": size,
                }
                stats["total_files"] += count
                stats["total_size_bytes"] += size

        return stats

    def cleanup_duplicates(self, dry_run: bool = True) -> int:
        """
        Remove duplicate files from duplicates directory

        Args:
            dry_run: If True, only log what would be deleted

        Returns:
            Number of files processed
        """
        dup_dir = self.organized_dir / "duplicates"

        if not dup_dir.exists():
            return 0

        count = 0
        for file_path in dup_dir.glob("*"):
            if file_path.is_file():
                if dry_run:
                    logger.info(f"Would delete duplicate: {file_path.name}")
                else:
                    file_path.unlink()
                    logger.info(f"Deleted duplicate: {file_path.name}")
                count += 1

        return count
