#!/usr/bin/env python3
"""
Comprehensive unit tests for verify_downloads.py

Tests cover:
- SHA-256 computation
- ZIP file verification
- File verification
- Manifest loading
- Directory verification
- Report generation
- CLI argument parsing

Target: 100% code coverage
"""

import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from verify_downloads import (
    compute_sha256,
    verify_zip_integrity,
    verify_file,
    load_manifest,
    verify_directory,
    verify_from_manifest,
    generate_report,
    VerificationResult,
    VerificationReport,
)


class TestComputeSHA256:
    """Test SHA-256 computation"""
    
    def test_compute_sha256_valid_file(self, tmp_path):
        """Test computing SHA-256 of a valid file"""
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)
        
        expected_hash = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        actual_hash = compute_sha256(test_file)
        
        assert actual_hash == expected_hash
    
    def test_compute_sha256_empty_file(self, tmp_path):
        """Test computing SHA-256 of an empty file"""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")
        
        # SHA-256 of empty string
        expected_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        actual_hash = compute_sha256(test_file)
        
        assert actual_hash == expected_hash
    
    def test_compute_sha256_large_file(self, tmp_path):
        """Test computing SHA-256 of a large file (> chunk size)"""
        test_file = tmp_path / "large.bin"
        # Create a 10MB file
        test_content = b"A" * (10 * 1024 * 1024)
        test_file.write_bytes(test_content)
        
        actual_hash = compute_sha256(test_file)
        
        # Verify hash is valid hex string of correct length
        assert len(actual_hash) == 64
        assert all(c in '0123456789abcdef' for c in actual_hash)
    
    def test_compute_sha256_nonexistent_file(self, tmp_path):
        """Test computing SHA-256 of nonexistent file"""
        test_file = tmp_path / "nonexistent.txt"
        
        actual_hash = compute_sha256(test_file)
        
        assert actual_hash == ""
    
    def test_compute_sha256_permission_error(self, tmp_path, monkeypatch):
        """Test handling permission error when reading file"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test")
        
        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr("builtins.open", mock_open)
        
        with patch('pathlib.Path.open', side_effect=PermissionError):
            actual_hash = compute_sha256(test_file)
            assert actual_hash == ""


class TestVerifyZipIntegrity:
    """Test ZIP file verification"""
    
    def test_verify_valid_zip(self, tmp_path):
        """Test verifying a valid ZIP file"""
        zip_file = tmp_path / "test.zip"
        
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")
        
        is_valid, error = verify_zip_integrity(zip_file)
        
        assert is_valid is True
        assert error is None
    
    def test_verify_empty_zip(self, tmp_path):
        """Test verifying an empty ZIP file"""
        zip_file = tmp_path / "empty.zip"
        
        with zipfile.ZipFile(zip_file, 'w') as zf:
            pass  # Create empty zip
        
        is_valid, error = verify_zip_integrity(zip_file)
        
        assert is_valid is True
        assert error is None
    
    def test_verify_corrupted_zip(self, tmp_path):
        """Test verifying a corrupted ZIP file"""
        zip_file = tmp_path / "corrupted.zip"
        zip_file.write_bytes(b"This is not a valid ZIP file")
        
        is_valid, error = verify_zip_integrity(zip_file)
        
        assert is_valid is False
        assert "Bad ZIP file" in error or "ZIP" in error
    
    def test_verify_truncated_zip(self, tmp_path):
        """Test verifying a truncated ZIP file"""
        zip_file = tmp_path / "truncated.zip"
        
        # Create a valid zip
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("file.txt", "content" * 1000)
        
        # Truncate it
        with zip_file.open('rb') as f:
            data = f.read()
        
        zip_file.write_bytes(data[:len(data) // 2])
        
        is_valid, error = verify_zip_integrity(zip_file)
        
        assert is_valid is False
        assert error is not None


class TestVerifyFile:
    """Test individual file verification"""
    
    def test_verify_existing_file(self, tmp_path):
        """Test verifying an existing file"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")
        
        result = verify_file(test_file)
        
        assert result.exists is True
        assert result.size_bytes == 12
        assert len(result.sha256) == 64
        assert result.is_valid is True
    
    def test_verify_nonexistent_file(self, tmp_path):
        """Test verifying a nonexistent file"""
        test_file = tmp_path / "nonexistent.txt"
        
        result = verify_file(test_file)
        
        assert result.exists is False
        assert result.size_bytes == 0
        assert result.is_valid is False
        assert "does not exist" in result.errors[0].lower()
    
    def test_verify_file_with_expected_size(self, tmp_path):
        """Test verifying file with expected size"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test")
        
        # Correct size
        result = verify_file(test_file, expected_size=4)
        assert result.size_matches is True
        assert result.is_valid is True
        
        # Wrong size
        result = verify_file(test_file, expected_size=10)
        assert result.size_matches is False
        assert result.is_valid is False
    
    def test_verify_file_with_expected_checksum(self, tmp_path):
        """Test verifying file with expected checksum"""
        test_file = tmp_path / "test.txt"
        test_content = b"test"
        test_file.write_bytes(test_content)
        
        # Compute correct checksum
        import hashlib
        correct_hash = hashlib.sha256(test_content).hexdigest()
        wrong_hash = "0" * 64
        
        # Correct checksum
        result = verify_file(test_file, expected_sha256=correct_hash)
        assert result.checksum_matches is True
        assert result.is_valid is True
        
        # Wrong checksum
        result = verify_file(test_file, expected_sha256=wrong_hash)
        assert result.checksum_matches is False
        assert result.is_valid is False
    
    def test_verify_valid_zip_file(self, tmp_path):
        """Test verifying a valid ZIP file"""
        zip_file = tmp_path / "test.zip"
        
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("file.txt", "content")
        
        result = verify_file(zip_file, verify_zip=True)
        
        assert result.is_valid_zip is True
        assert result.zip_error is None
        assert result.is_valid is True
    
    def test_verify_corrupted_zip_file(self, tmp_path):
        """Test verifying a corrupted ZIP file"""
        zip_file = tmp_path / "bad.zip"
        zip_file.write_bytes(b"not a zip")
        
        result = verify_file(zip_file, verify_zip=True)
        
        assert result.is_valid_zip is False
        assert result.zip_error is not None
        assert result.is_valid is False
    
    def test_verify_file_skip_zip_check(self, tmp_path):
        """Test verifying ZIP file with skip_zip=True"""
        zip_file = tmp_path / "test.zip"
        zip_file.write_bytes(b"not a zip")
        
        result = verify_file(zip_file, verify_zip=False)
        
        assert result.is_valid_zip is None
        assert result.is_valid is True  # Should pass without ZIP check
    
    def test_verify_file_verbose(self, tmp_path, capsys):
        """Test verifying file with verbose output"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test")
        
        result = verify_file(test_file, verbose=True)
        
        captured = capsys.readouterr()
        assert "Computing SHA-256" in captured.out
        assert "Verified successfully" in captured.out


class TestLoadManifest:
    """Test manifest loading"""
    
    def test_load_valid_manifest(self, tmp_path):
        """Test loading a valid manifest file"""
        manifest_file = tmp_path / "manifest.jsonl"
        
        entries = [
            {"dest": "file1.txt", "sha256": "abc123", "bytes": 100},
            {"dest": "file2.txt", "sha256": "def456", "bytes": 200},
        ]
        
        with manifest_file.open('w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        loaded = load_manifest(manifest_file)
        
        assert len(loaded) == 2
        assert loaded[0]['dest'] == 'file1.txt'
        assert loaded[1]['sha256'] == 'def456'
    
    def test_load_empty_manifest(self, tmp_path):
        """Test loading an empty manifest file"""
        manifest_file = tmp_path / "empty.jsonl"
        manifest_file.write_text("")
        
        loaded = load_manifest(manifest_file)
        
        assert len(loaded) == 0
    
    def test_load_manifest_with_blank_lines(self, tmp_path):
        """Test loading manifest with blank lines"""
        manifest_file = tmp_path / "manifest.jsonl"
        
        with manifest_file.open('w') as f:
            f.write('{"dest": "file1.txt"}\n')
            f.write('\n')
            f.write('{"dest": "file2.txt"}\n')
            f.write('  \n')
        
        loaded = load_manifest(manifest_file)
        
        assert len(loaded) == 2
    
    def test_load_nonexistent_manifest(self, tmp_path):
        """Test loading nonexistent manifest"""
        manifest_file = tmp_path / "nonexistent.jsonl"
        
        loaded = load_manifest(manifest_file)
        
        assert len(loaded) == 0
    
    def test_load_corrupted_manifest(self, tmp_path):
        """Test loading manifest with invalid JSON"""
        manifest_file = tmp_path / "corrupted.jsonl"
        manifest_file.write_text("not json\n{invalid json}\n")
        
        loaded = load_manifest(manifest_file)
        
        assert len(loaded) == 0


class TestVerifyDirectory:
    """Test directory verification"""
    
    def test_verify_directory_with_files(self, tmp_path):
        """Test verifying directory containing files"""
        (tmp_path / "file1.txt").write_bytes(b"content1")
        (tmp_path / "file2.txt").write_bytes(b"content2")
        
        report = verify_directory(tmp_path, recursive=False)
        
        assert report.total_files == 2
        assert report.verified == 2
        assert report.failed == 0
    
    def test_verify_directory_recursive(self, tmp_path):
        """Test verifying directory recursively"""
        (tmp_path / "file1.txt").write_bytes(b"content1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_bytes(b"content2")
        
        report = verify_directory(tmp_path, recursive=True)
        
        assert report.total_files == 2
    
    def test_verify_directory_non_recursive(self, tmp_path):
        """Test verifying directory non-recursively"""
        (tmp_path / "file1.txt").write_bytes(b"content1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_bytes(b"content2")
        
        report = verify_directory(tmp_path, recursive=False)
        
        assert report.total_files == 1  # Only top-level file
    
    def test_verify_empty_directory(self, tmp_path):
        """Test verifying empty directory"""
        report = verify_directory(tmp_path)
        
        assert report.total_files == 0
        assert report.verified == 0
    
    def test_verify_nonexistent_directory(self, tmp_path):
        """Test verifying nonexistent directory"""
        nonexistent = tmp_path / "nonexistent"
        
        report = verify_directory(nonexistent)
        
        assert report.total_files == 0


class TestVerifyFromManifest:
    """Test manifest-based verification"""
    
    def test_verify_from_valid_manifest(self, tmp_path):
        """Test verifying files from a valid manifest"""
        # Create files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")
        
        # Create manifest
        import hashlib
        manifest_file = tmp_path / "manifest.jsonl"
        with manifest_file.open('w') as f:
            f.write(json.dumps({
                "dest": str(file1),
                "sha256": hashlib.sha256(b"content1").hexdigest(),
                "bytes": 8
            }) + '\n')
            f.write(json.dumps({
                "dest": str(file2),
                "sha256": hashlib.sha256(b"content2").hexdigest(),
                "bytes": 8
            }) + '\n')
        
        report = verify_from_manifest(manifest_file)
        
        assert report.total_files == 2
        assert report.verified == 2
        assert report.failed == 0
    
    def test_verify_from_manifest_with_missing_files(self, tmp_path):
        """Test verifying with missing files"""
        manifest_file = tmp_path / "manifest.jsonl"
        with manifest_file.open('w') as f:
            f.write(json.dumps({
                "dest": str(tmp_path / "nonexistent.txt"),
                "sha256": "abc123",
                "bytes": 100
            }) + '\n')
        
        report = verify_from_manifest(manifest_file)
        
        assert report.total_files == 1
        assert report.missing == 1
        assert report.verified == 0
    
    def test_verify_from_empty_manifest(self, tmp_path):
        """Test verifying from empty manifest"""
        manifest_file = tmp_path / "empty.jsonl"
        manifest_file.write_text("")
        
        report = verify_from_manifest(manifest_file)
        
        assert report.total_files == 0


class TestGenerateReport:
    """Test report generation"""
    
    def test_generate_report_all_valid(self):
        """Test generating report with all valid files"""
        results = [
            VerificationResult(filepath="file1.txt", exists=True, size_bytes=100, sha256="abc"),
            VerificationResult(filepath="file2.txt", exists=True, size_bytes=200, sha256="def"),
        ]
        
        report = generate_report(results)
        
        assert report.total_files == 2
        assert report.verified == 2
        assert report.failed == 0
        assert report.missing == 0
    
    def test_generate_report_with_failures(self):
        """Test generating report with failures"""
        results = [
            VerificationResult(filepath="file1.txt", exists=True, size_bytes=100, sha256="abc"),
            VerificationResult(filepath="file2.txt", exists=False, size_bytes=0, errors=["missing"]),
        ]
        
        report = generate_report(results)
        
        assert report.total_files == 2
        assert report.verified == 1
        assert report.failed == 1
        assert report.missing == 1
    
    def test_generate_report_with_mismatches(self):
        """Test generating report with checksum/size mismatches"""
        result1 = VerificationResult(filepath="file1.txt", exists=True, size_bytes=100, sha256="abc")
        result1.size_matches = False
        
        result2 = VerificationResult(filepath="file2.txt", exists=True, size_bytes=200, sha256="def")
        result2.checksum_matches = False
        
        result3 = VerificationResult(filepath="file3.zip", exists=True, size_bytes=300, sha256="ghi")
        result3.is_valid_zip = False
        
        report = generate_report([result1, result2, result3])
        
        assert report.size_mismatches == 1
        assert report.checksum_mismatches == 1
        assert report.corrupted_zips == 1
    
    def test_generate_empty_report(self):
        """Test generating report with no results"""
        report = generate_report([])
        
        assert report.total_files == 0
        assert report.verified == 0
        assert report.failed == 0


class TestVerificationResult:
    """Test VerificationResult class"""
    
    def test_is_valid_all_good(self):
        """Test is_valid when all checks pass"""
        result = VerificationResult(
            filepath="test.txt",
            exists=True,
            size_bytes=100,
            size_matches=True,
            sha256="abc",
            checksum_matches=True
        )
        
        assert result.is_valid is True
    
    def test_is_valid_missing_file(self):
        """Test is_valid when file doesn't exist"""
        result = VerificationResult(
            filepath="test.txt",
            exists=False,
            size_bytes=0
        )
        
        assert result.is_valid is False
    
    def test_is_valid_with_errors(self):
        """Test is_valid when errors present"""
        result = VerificationResult(
            filepath="test.txt",
            exists=True,
            size_bytes=100,
            errors=["some error"]
        )
        
        assert result.is_valid is False
    
    def test_is_valid_with_zip_failure(self):
        """Test is_valid when ZIP check fails"""
        result = VerificationResult(
            filepath="test.zip",
            exists=True,
            size_bytes=100,
            is_valid_zip=False
        )
        
        assert result.is_valid is False
    
    def test_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated"""
        result = VerificationResult(
            filepath="test.txt",
            exists=True,
            size_bytes=100
        )
        
        assert result.timestamp != ""
        assert "T" in result.timestamp  # ISO format


class TestVerificationReport:
    """Test VerificationReport class"""
    
    def test_timestamp_auto_generated(self):
        """Test that report timestamp is auto-generated"""
        report = VerificationReport(
            total_files=0,
            verified=0,
            failed=0,
            missing=0,
            checksum_mismatches=0,
            size_mismatches=0,
            corrupted_zips=0,
            results=[]
        )
        
        assert report.timestamp != ""
        assert "T" in report.timestamp  # ISO format


class TestCLI:
    """Test CLI functionality"""
    
    def test_help_message(self):
        """Test that --help works"""
        from verify_downloads import main
        
        with pytest.raises(SystemExit) as exc_info:
            with patch('sys.argv', ['verify_downloads.py', '--help']):
                main()
        
        assert exc_info.value.code == 0
    
    def test_missing_arguments(self):
        """Test that script requires --dir or --manifest"""
        from verify_downloads import main
        
        with pytest.raises(SystemExit):
            with patch('sys.argv', ['verify_downloads.py']):
                main()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=verify_downloads', '--cov-report=html', '--cov-report=term'])
