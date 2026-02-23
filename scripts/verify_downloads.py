#!/usr/bin/env python3
"""
Verification script for downloaded Epstein files.

This script verifies the integrity of downloaded files by:
1. Checking file existence
2. Validating file sizes
3. Computing and verifying SHA-256 checksums
4. Validating ZIP file integrity
5. Generating verification reports

Usage:
    python scripts/verify_downloads.py --dir ./epstein_project/raw
    python scripts/verify_downloads.py --manifest ./epstein_project/manifests/doj_disclosures.manifest.jsonl
    python scripts/verify_downloads.py --dir ./downloads --verbose --report verification_report.json
"""

import argparse
import hashlib
import json
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class VerificationResult:
    """Result of verifying a single file"""
    filepath: str
    exists: bool
    size_bytes: int
    expected_size: int | None = None
    size_matches: bool = True
    sha256: str = ""
    expected_sha256: str | None = None
    checksum_matches: bool = True
    is_valid_zip: bool | None = None
    zip_error: str | None = None
    errors: list[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    @property
    def is_valid(self) -> bool:
        """Check if file passed all verifications"""
        return (self.exists and
                self.size_matches and
                self.checksum_matches and
                (self.is_valid_zip is None or self.is_valid_zip) and
                len(self.errors) == 0)


@dataclass
class VerificationReport:
    """Overall verification report"""
    total_files: int
    verified: int
    failed: int
    missing: int
    checksum_mismatches: int
    size_mismatches: int
    corrupted_zips: int
    results: list[VerificationResult]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


def compute_sha256(filepath: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        filepath: Path to the file
        chunk_size: Size of chunks to read (default 8MB)

    Returns:
        Hexadecimal SHA-256 hash string
    """
    hasher = hashlib.sha256()
    try:
        with filepath.open('rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"❌ Error computing SHA-256 for {filepath}: {e}", file=sys.stderr)
        return ""


def verify_zip_integrity(filepath: Path) -> tuple[bool, str | None]:
    """
    Verify ZIP file integrity.

    Args:
        filepath: Path to ZIP file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            # Test all members
            corrupt_member = zf.testzip()
            if corrupt_member is not None:
                return False, f"Corrupt ZIP member: {corrupt_member}"
            return True, None
    except zipfile.BadZipFile as e:
        return False, f"Bad ZIP file: {e}"
    except Exception as e:
        return False, f"ZIP verification error: {e}"


def verify_file(
    filepath: Path,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    verify_zip: bool = True,
    verbose: bool = False
) -> VerificationResult:
    """
    Verify a single file.

    Args:
        filepath: Path to file to verify
        expected_size: Expected file size in bytes (optional)
        expected_sha256: Expected SHA-256 hash (optional)
        verify_zip: Whether to verify ZIP integrity if file is a ZIP
        verbose: Print verbose output

    Returns:
        VerificationResult object
    """
    result = VerificationResult(
        filepath=str(filepath),
        exists=False,
        size_bytes=0
    )

    # Check existence
    if not filepath.exists():
        result.errors.append("File does not exist")
        if verbose:
            print(f"❌ {filepath.name}: Does not exist")
        return result

    result.exists = True

    # Check size
    try:
        result.size_bytes = filepath.stat().st_size
        result.expected_size = expected_size

        if expected_size is not None:
            result.size_matches = (result.size_bytes == expected_size)
            if not result.size_matches:
                result.errors.append(
                    f"Size mismatch: got {result.size_bytes}, expected {expected_size}"
                )
                if verbose:
                    print(f"⚠️  {filepath.name}: Size mismatch")
    except Exception as e:
        result.errors.append(f"Error checking size: {e}")
        if verbose:
            print(f"❌ {filepath.name}: Error checking size")

    # Compute and verify checksum
    if verbose:
        print(f"🔍 {filepath.name}: Computing SHA-256...")

    result.sha256 = compute_sha256(filepath)
    result.expected_sha256 = expected_sha256

    if result.sha256 and expected_sha256:
        result.checksum_matches = (result.sha256.lower() == expected_sha256.lower())
        if not result.checksum_matches:
            result.errors.append("SHA-256 checksum mismatch")
            if verbose:
                print(f"❌ {filepath.name}: Checksum mismatch")
    elif not result.sha256:
        result.errors.append("Failed to compute SHA-256")
        if verbose:
            print(f"❌ {filepath.name}: Failed to compute checksum")

    # Verify ZIP integrity if applicable
    if verify_zip and filepath.suffix.lower() == '.zip':
        if verbose:
            print(f"📦 {filepath.name}: Verifying ZIP integrity...")

        is_valid, error_msg = verify_zip_integrity(filepath)
        result.is_valid_zip = is_valid
        result.zip_error = error_msg

        if not is_valid:
            result.errors.append(f"ZIP integrity check failed: {error_msg}")
            if verbose:
                print(f"❌ {filepath.name}: ZIP integrity check failed")

    # Report success
    if result.is_valid and verbose:
        print(f"✅ {filepath.name}: Verified successfully")

    return result


def load_manifest(manifest_path: Path) -> list[dict]:
    """
    Load a JSONL manifest file.

    Args:
        manifest_path: Path to manifest file

    Returns:
        List of manifest entries
    """
    entries = []
    try:
        with manifest_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception as e:
        print(f"❌ Error loading manifest {manifest_path}: {e}", file=sys.stderr)
    return entries


def verify_directory(
    directory: Path,
    recursive: bool = True,
    verify_zip: bool = True,
    verbose: bool = False
) -> VerificationReport:
    """
    Verify all files in a directory.

    Args:
        directory: Directory to verify
        recursive: Recursively verify subdirectories
        verify_zip: Verify ZIP file integrity
        verbose: Print verbose output

    Returns:
        VerificationReport object
    """
    if not directory.exists():
        print(f"❌ Directory does not exist: {directory}", file=sys.stderr)
        return VerificationReport(
            total_files=0,
            verified=0,
            failed=0,
            missing=0,
            checksum_mismatches=0,
            size_mismatches=0,
            corrupted_zips=0,
            results=[]
        )

    # Find all files
    if recursive:
        files = [f for f in directory.rglob('*') if f.is_file()]
    else:
        files = [f for f in directory.glob('*') if f.is_file()]

    if verbose:
        print(f"📂 Found {len(files)} file(s) in {directory}")

    results = []
    for filepath in files:
        result = verify_file(filepath, verify_zip=verify_zip, verbose=verbose)
        results.append(result)

    # Generate report
    report = generate_report(results)
    return report


def verify_from_manifest(
    manifest_path: Path,
    base_dir: Path | None = None,
    verify_zip: bool = True,
    verbose: bool = False
) -> VerificationReport:
    """
    Verify files listed in a manifest.

    Args:
        manifest_path: Path to manifest file
        base_dir: Base directory for relative paths
        verify_zip: Verify ZIP file integrity
        verbose: Print verbose output

    Returns:
        VerificationReport object
    """
    entries = load_manifest(manifest_path)

    if not entries:
        print(f"⚠️  No entries found in manifest: {manifest_path}", file=sys.stderr)
        return VerificationReport(
            total_files=0,
            verified=0,
            failed=0,
            missing=0,
            checksum_mismatches=0,
            size_mismatches=0,
            corrupted_zips=0,
            results=[]
        )

    if verbose:
        print(f"📋 Found {len(entries)} entry/entries in manifest")

    results = []
    for entry in entries:
        dest = entry.get('dest', '')
        filepath = Path(dest)

        # Handle relative paths
        if base_dir and not filepath.is_absolute():
            filepath = base_dir / filepath

        expected_size = entry.get('bytes')
        expected_sha256 = entry.get('sha256')

        result = verify_file(
            filepath,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
            verify_zip=verify_zip,
            verbose=verbose
        )
        results.append(result)

    report = generate_report(results)
    return report


def generate_report(results: list[VerificationResult]) -> VerificationReport:
    """
    Generate a verification report from results.

    Args:
        results: List of VerificationResult objects

    Returns:
        VerificationReport object
    """
    total = len(results)
    verified = sum(1 for r in results if r.is_valid)
    failed = total - verified
    missing = sum(1 for r in results if not r.exists)
    checksum_mismatches = sum(1 for r in results if not r.checksum_matches)
    size_mismatches = sum(1 for r in results if not r.size_matches)
    corrupted_zips = sum(1 for r in results if r.is_valid_zip is False)

    return VerificationReport(
        total_files=total,
        verified=verified,
        failed=failed,
        missing=missing,
        checksum_mismatches=checksum_mismatches,
        size_mismatches=size_mismatches,
        corrupted_zips=corrupted_zips,
        results=results
    )


def print_report(report: VerificationReport, detailed: bool = False):
    """
    Print verification report to console.

    Args:
        report: VerificationReport object
        detailed: Print detailed results for each file
    """
    print("\n" + "=" * 60)
    print("📊 VERIFICATION REPORT")
    print("=" * 60)
    print(f"Total Files:          {report.total_files}")
    print(f"✅ Verified:          {report.verified}")
    print(f"❌ Failed:            {report.failed}")
    print(f"🔍 Missing:           {report.missing}")
    print(f"⚠️  Checksum Mismatch: {report.checksum_mismatches}")
    print(f"📏 Size Mismatch:     {report.size_mismatches}")
    print(f"📦 Corrupted ZIPs:    {report.corrupted_zips}")
    print(f"⏰ Timestamp:         {report.timestamp}")
    print("=" * 60)

    if detailed:
        print("\n📋 DETAILED RESULTS:")
        print("-" * 60)
        for result in report.results:
            status = "✅" if result.is_valid else "❌"
            print(f"\n{status} {Path(result.filepath).name}")
            print(f"   Path: {result.filepath}")
            print(f"   Exists: {result.exists}")
            if result.exists:
                print(f"   Size: {result.size_bytes:,} bytes")
                if result.expected_size:
                    print(f"   Expected Size: {result.expected_size:,} bytes")
                if result.sha256:
                    print(f"   SHA-256: {result.sha256}")
                if result.expected_sha256:
                    print(f"   Expected SHA-256: {result.expected_sha256}")
                if result.is_valid_zip is not None:
                    zip_status = "Valid" if result.is_valid_zip else "Invalid"
                    print(f"   ZIP Status: {zip_status}")
                    if result.zip_error:
                        print(f"   ZIP Error: {result.zip_error}")
            if result.errors:
                print("   Errors:")
                for error in result.errors:
                    print(f"     - {error}")

    # Exit status based on verification
    success_rate = (report.verified / report.total_files * 100) if report.total_files > 0 else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}%")

    if report.failed > 0:
        print("\n⚠️  Some files failed verification!")
    else:
        print("\n✅ All files verified successfully!")


def save_report(report: VerificationReport, output_path: Path):
    """
    Save verification report to JSON file.

    Args:
        report: VerificationReport object
        output_path: Path to save report
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report_dict = asdict(report)

        with output_path.open('w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Report saved to: {output_path}")
    except Exception as e:
        print(f"\n❌ Error saving report: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Verify integrity of downloaded Epstein files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify all files in a directory
  python scripts/verify_downloads.py --dir ./epstein_project/raw

  # Verify files from a manifest
  python scripts/verify_downloads.py --manifest ./manifests/doj_disclosures.manifest.jsonl

  # Verify with detailed output and save report
  python scripts/verify_downloads.py --dir ./downloads --verbose --detailed --report report.json

  # Skip ZIP integrity checks
  python scripts/verify_downloads.py --dir ./downloads --no-verify-zip
        """
    )

    parser.add_argument(
        '--dir',
        type=Path,
        help='Directory containing files to verify'
    )
    parser.add_argument(
        '--manifest',
        type=Path,
        help='Manifest file (JSONL format) containing file metadata'
    )
    parser.add_argument(
        '--base-dir',
        type=Path,
        help='Base directory for resolving relative paths in manifest'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=True,
        help='Recursively verify subdirectories (default: True)'
    )
    parser.add_argument(
        '--no-recursive',
        dest='recursive',
        action='store_false',
        help='Do not recursively verify subdirectories'
    )
    parser.add_argument(
        '--verify-zip',
        action='store_true',
        default=True,
        help='Verify ZIP file integrity (default: True)'
    )
    parser.add_argument(
        '--no-verify-zip',
        dest='verify_zip',
        action='store_false',
        help='Skip ZIP file integrity verification'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print verbose output during verification'
    )
    parser.add_argument(
        '--detailed',
        '-d',
        action='store_true',
        help='Print detailed results for each file in report'
    )
    parser.add_argument(
        '--report',
        '-r',
        type=Path,
        help='Save verification report to JSON file'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.dir and not args.manifest:
        parser.error("Either --dir or --manifest must be specified")

    if args.dir and args.manifest:
        parser.error("Cannot specify both --dir and --manifest")

    # Run verification
    if args.dir:
        print(f"🔍 Verifying directory: {args.dir}")
        report = verify_directory(
            args.dir,
            recursive=args.recursive,
            verify_zip=args.verify_zip,
            verbose=args.verbose
        )
    else:
        print(f"🔍 Verifying from manifest: {args.manifest}")
        report = verify_from_manifest(
            args.manifest,
            base_dir=args.base_dir,
            verify_zip=args.verify_zip,
            verbose=args.verbose
        )

    # Print report
    print_report(report, detailed=args.detailed)

    # Save report if requested
    if args.report:
        save_report(report, args.report)

    # Exit with appropriate code
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == '__main__':
    main()
