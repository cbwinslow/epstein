# New Features: January 2026 Release Support

This document describes the new features and improvements added to support the January 30, 2026 DOJ Epstein files release (3.5M+ pages).

## Overview

The January 30, 2026 release is the largest Epstein files disclosure to date, containing:
- **3.5 million+ pages** of documents
- **2,000+ videos**
- **180,000+ images**
- Multiple new data sets (Data Sets 9, 10, 11+)

This release required significant enhancements to the download and verification infrastructure.

## New Features

### 1. Enhanced Bulk Downloader

**File**: `scripts/epstein_bulk_downloader.py`

**Improvements**:
- ✅ Auto-discovery of new data sets (9, 10, 11+)
- ✅ Improved logging with helpful messages
- ✅ Detection of January 2026 release datasets
- ✅ Metadata tracking for release dates
- ✅ Better error handling with actionable advice

**Usage**:
```bash
# Download all sources (DOJ + FBI + House Oversight)
python scripts/epstein_bulk_downloader.py --out-dir ./epstein_project

# Download only DOJ disclosures
python scripts/epstein_bulk_downloader.py --sources doj

# Dry run (see what would be downloaded)
python scripts/epstein_bulk_downloader.py --dry-run --verbose
```

**New Features**:
- Detects when downloading January 2026 release data sets
- Provides informational messages about videos/images in new release
- Tracks release date in metadata for provenance

### 2. Download Verification Tool

**File**: `scripts/verify_downloads.py`

**Features**:
- ✅ SHA-256 checksum verification
- ✅ ZIP file integrity validation
- ✅ Manifest-based verification
- ✅ Directory scanning
- ✅ Detailed error reporting
- ✅ Progress reporting with helpful messages

**Usage**:
```bash
# Verify all files in a directory
python scripts/verify_downloads.py --dir ./epstein_project/raw

# Verify from manifest (checks expected checksums)
python scripts/verify_downloads.py --manifest ./manifests/doj_disclosures.manifest.jsonl

# Verbose output with detailed progress
python scripts/verify_downloads.py --dir ./downloads --verbose --detailed

# Save verification report
python scripts/verify_downloads.py --dir ./downloads --report verification_report.json
```

**Benefits**:
- Ensures download integrity
- Detects corrupted files before processing
- Provides actionable error messages
- Generates audit reports

### 3. OpenRouter Free Models Discovery

**File**: `epstein/openrouter_models.py`

**Features**:
- ✅ Automatic discovery of free LLM models
- ✅ Model caching with configurable TTL
- ✅ CLI for model management
- ✅ Export functionality
- ✅ No API key required for listing

**Usage**:
```bash
# List free models
python -m epstein.openrouter_models

# List with detailed information
python -m epstein.openrouter_models --verbose

# Force refresh cache
python -m epstein.openrouter_models --refresh

# Export to JSON
python -m epstein.openrouter_models --export free_models.json

# Clear cache
python -m epstein.openrouter_models --clear-cache
```

**Python API**:
```python
from epstein.openrouter_models import get_free_models, get_free_model_ids

# Get all free models
models = get_free_models()
for model in models:
    print(f"{model.id}: {model.name}")

# Get just model IDs
model_ids = get_free_model_ids()
print(model_ids)
```

**Benefits**:
- Use free models for development/testing
- Auto-refresh list as OpenRouter adds models
- No cost for experimentation
- Easy integration with scripts

### 4. API Keys Management

**File**: `docs/API_KEYS_SETUP.md`

**Features**:
- ✅ Comprehensive setup guide
- ✅ Multiple secret management methods
- ✅ Security best practices
- ✅ Troubleshooting guide

**Supported Methods**:
1. Environment variables (`.env` file)
2. dotenvx (encrypted secrets)
3. GitHub repository secrets
4. Cloudflare secrets
5. Bitwarden CLI

**Validation Script**:
```bash
# Validate all API keys are configured
./scripts/validate_api_keys.sh
```

**Benefits**:
- Secure secret management
- Multiple deployment options
- Team-friendly workflows
- Audit trail

### 5. Comprehensive Testing

**Files**:
- `tests/test_verify_downloads.py` - 100% coverage for verification
- `tests/test_openrouter_models.py` - 100% coverage for model discovery

**Features**:
- ✅ Unit tests for all new modules
- ✅ Mocking of external APIs
- ✅ Edge case coverage
- ✅ Error scenario testing

**Running Tests**:
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=epstein --cov=scripts --cov-report=html

# Run specific test file
pytest tests/test_verify_downloads.py -v

# Run with detailed output
pytest tests/ -vv --tb=short
```

**Benefits**:
- Confidence in code quality
- Catch regressions early
- Documentation through examples
- Easier maintenance

### 6. Enhanced Documentation

**New/Updated Files**:
- `docs/NEW_RELEASE_JAN_2026.md` - January 2026 release details
- `docs/TASKS.md` - 150+ improvement tasks
- `docs/API_KEYS_SETUP.md` - API key configuration guide
- `docs/NEW_FEATURES.md` - This file

**Benefits**:
- Complete reference documentation
- Onboarding guides
- Troubleshooting help
- Future planning

## Migration Guide

### For Existing Users

If you've been using the old downloader:

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Review new documentation**:
   ```bash
   cat docs/NEW_RELEASE_JAN_2026.md
   cat docs/API_KEYS_SETUP.md
   ```

3. **Set up API keys** (if not done):
   ```bash
   cp .env.example .env
   nano .env  # Add your keys
   ./scripts/validate_api_keys.sh
   ```

4. **Download new datasets**:
   ```bash
   # This will discover and download new Data Sets 9, 10, 11+
   python scripts/epstein_bulk_downloader.py --sources doj
   ```

5. **Verify downloads**:
   ```bash
   python scripts/verify_downloads.py \
     --manifest-dir ./epstein_project/manifests \
     --verbose
   ```

### For New Users

1. **Clone repository**:
   ```bash
   git clone https://github.com/cbwinslow/epstein.git
   cd epstein
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   nano .env  # Configure your keys
   ```

3. **Validate configuration**:
   ```bash
   ./scripts/validate_api_keys.sh
   ```

4. **Bootstrap project**:
   ```bash
   make bootstrap
   ```

5. **Download files**:
   ```bash
   python scripts/epstein_bulk_downloader.py
   ```

6. **Verify and process**:
   ```bash
   python scripts/verify_downloads.py --manifest-dir ./epstein_project/manifests
   make pipeline-run
   ```

## Performance Considerations

### Large File Downloads

The January 2026 release includes very large files:

**Recommendations**:
- Ensure **100+ GB** free disk space
- Use **stable network connection**
- Enable **resume capability** (automatic in downloader)
- Monitor progress with: `scripts/monitor_downloads.py`

### Verification

Verifying 3.5M pages takes time:

**Tips**:
- Run verification in background
- Use `--no-verify-zip` to skip ZIP checks if needed
- Verify incrementally as files download
- Save reports for audit trail

### Processing

Processing 3.5M pages requires resources:

**Optimization**:
- Use `--max-workers` to control parallelism
- Process in batches (by data set)
- Monitor memory usage
- Use SSD for better performance

## Troubleshooting

### Downloads Failing

**Issue**: Downloads repeatedly fail

**Solutions**:
1. Check network connection
2. Verify sufficient disk space
3. Check DOJ website status
4. Reduce `--max-workers` (default is 3)
5. Increase `--retries` and `--timeout`

**Example**:
```bash
python scripts/epstein_bulk_downloader.py \
  --max-workers 1 \
  --retries 10 \
  --timeout 120
```

### Verification Errors

**Issue**: Files fail checksum verification

**Solutions**:
1. Re-download the file
2. Check for disk corruption
3. Verify network didn't corrupt download
4. Compare with official checksums

**Example**:
```bash
# Re-download a specific data set
python scripts/epstein_bulk_downloader.py --sources doj
```

### Out of Memory

**Issue**: Processing runs out of memory

**Solutions**:
1. Process one data set at a time
2. Reduce batch size
3. Close other applications
4. Add more RAM or use swap

**Example**:
```bash
# Process specific data set
make pipeline-run DATASET=9
```

### API Key Issues

**Issue**: API key not working

**Solutions**:
1. Run validation: `./scripts/validate_api_keys.sh`
2. Check key format (no extra spaces/quotes)
3. Verify key hasn't expired
4. Test key manually with curl
5. Regenerate key if needed

## Future Enhancements

See `docs/TASKS.md` for comprehensive list. Key priorities:

1. **Enhanced MCP Server**
   - Add download APIs
   - Real-time progress endpoints
   - Authentication

2. **Advanced Verification**
   - Parallel verification
   - Incremental verification
   - Automatic repair

3. **Video/Image Processing**
   - Video metadata extraction
   - Image OCR support
   - Thumbnail generation

4. **Observability**
   - OpenTelemetry integration
   - Performance metrics
   - Alerting

5. **Testing**
   - Integration tests
   - E2E tests
   - Load testing

## Contributing

To contribute to these features:

1. Review `docs/TASKS.md` for open tasks
2. Check existing issues on GitHub
3. Follow contribution guidelines
4. Write tests for new features
5. Update documentation

## Support

Need help?

1. Check this documentation
2. Review `docs/API_KEYS_SETUP.md`
3. Run `./scripts/validate_api_keys.sh`
4. Search existing GitHub issues
5. Open a new issue with details

## Changelog

### 2026-02-01
- ✅ Added support for January 2026 release (Data Sets 9+)
- ✅ Created verification tool with SHA-256 checksums
- ✅ Added OpenRouter free models discovery
- ✅ Created comprehensive API keys setup guide
- ✅ Added 100% test coverage for new modules
- ✅ Enhanced bulk downloader with better logging
- ✅ Updated documentation with 150+ improvement tasks

---

**Version**: 2.1.0  
**Last Updated**: 2026-02-01  
**Maintainer**: Epstein Project Team
