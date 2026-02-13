# DOJ Epstein Files Automation System

## Overview

The DOJ Epstein Files Automation System is a comprehensive, modular pipeline for automatically downloading, organizing, and processing Epstein-related documents from multiple government sources. This system provides end-to-end automation with monitoring, error handling, and quality validation.

## Features

### Core Capabilities

1. **Automated Downloads**
   - Multi-source support (DOJ, FBI, House Oversight, GovInfo)
   - Session/cookie authentication
   - Resumable downloads with retry logic
   - Concurrent downloads with rate limiting
   - SHA-256 checksum verification
   - Comprehensive download manifests

2. **File Organization**
   - Automatic unzipping with Zip Slip protection
   - Category-based organization
   - Consistent naming conventions
   - Deduplication by hash
   - Metadata tracking
   - File type detection

3. **OCR Processing**
   - Automated OCR with Tesseract
   - Quality validation and scoring
   - Text extraction and validation
   - Parallel processing support
   - Retry logic for failures
   - Coverage metrics

4. **Monitoring & Logging**
   - Real-time progress tracking
   - Rich terminal dashboards
   - Comprehensive metrics collection
   - Alert system (multiple severity levels)
   - Audit trail (JSONL format)
   - Detailed reporting

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Pipeline Orchestrator                       │
│         (Coordinates all components)                     │
└──────┬────────────┬────────────┬────────────┬───────────┘
       │            │            │            │
       ▼            ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│Download  │ │   File   │ │   OCR    │ │  Operation   │
│ Manager  │ │Organizer │ │Processor │ │  Monitor     │
└──────────┘ └──────────┘ └──────────┘ └──────────────┘
       │            │            │            │
       └────────────┴────────────┴────────────┘
                     │
           ┌─────────▼──────────┐
           │  Data Storage      │
           │  (Organized Files) │
           └────────────────────┘
```

## Components

### 1. Download Manager (`epstein/download_manager.py`)

Handles file downloads with:
- Session-based authentication (cookies, auth keys)
- Resumable downloads
- Concurrent download support
- Progress tracking
- Checksum verification
- Manifest generation

**Usage:**
```python
from epstein.download_manager import DownloadManager, DownloadTask, DownloadSource, SessionConfig

# Configure session with authentication
session_config = SessionConfig(
    user_agent="My-Downloader/1.0",
    cookies={"session": "your_session_cookie"},
    session_key="your_api_key"  # Optional
)

# Create manager
manager = DownloadManager(
    output_dir=Path("./downloads"),
    max_concurrent=3,
    session_config=session_config
)

# Add download task
task = DownloadTask(
    url="https://example.com/file.pdf",
    destination=Path("./downloads/file.pdf"),
    source=DownloadSource.DOJ_DISCLOSURES,
    name="Sample File"
)
task_id = manager.add_task(task)

# Download with retry
success, error = manager.download_with_retry(task_id)

# Get statistics
stats = manager.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
```

### 2. File Organizer (`epstein/file_organizer.py`)

Organizes downloaded files with:
- Automatic categorization
- Naming convention enforcement
- ZIP extraction with safety checks
- Hash-based deduplication
- Metadata tracking

**Usage:**
```python
from epstein.file_organizer import FileOrganizer

# Create organizer
organizer = FileOrganizer(
    base_dir=Path("./downloads"),
    organized_dir=Path("./organized"),
    dedup_enabled=True,
    auto_extract_zips=True
)

# Organize a single file
success, organized_path, error = organizer.organize_file(
    file_path=Path("./downloads/document.pdf"),
    source="doj_disclosures",
    dataset_number=1
)

# Organize entire directory
stats = organizer.organize_directory(
    directory=Path("./downloads"),
    source="doj_disclosures",
    recursive=True
)
print(f"Organized {stats['success']}/{stats['total']} files")
```

### 3. OCR Processor (`epstein/ocr_processor.py`)

Processes PDFs with OCR:
- Quality assessment
- Text extraction
- Parallel processing
- Retry logic
- Comprehensive metrics

**Usage:**
```python
from epstein.ocr_processor import OCRProcessor, OCRQuality

# Create processor
processor = OCRProcessor(
    output_dir=Path("./ocr_output"),
    max_workers=2,
    quality_threshold=OCRQuality.ACCEPTABLE
)

# Add tasks
pdf_files = list(Path("./organized").glob("**/*.pdf"))
task_ids = processor.add_batch_tasks(pdf_files)

# Process with parallel execution
results = processor.process_batch(task_ids, parallel=True)

# Get statistics
stats = processor.get_statistics()
print(f"OCR completed: {stats['completed']}/{stats['total_tasks']}")
print(f"Average quality: {stats['average_confidence_score']:.1f}%")
```

### 4. Operation Monitor (`epstein/operation_monitor.py`)

Monitors operations with:
- Real-time progress tracking
- Alert generation
- Metrics collection
- Audit trail
- Dashboard visualization

**Usage:**
```python
from epstein.operation_monitor import OperationMonitor, OperationType

# Create monitor
monitor = OperationMonitor(
    log_dir=Path("./logs"),
    enable_dashboard=True,
    enable_alerts=True
)

# Track an operation
monitor.start_operation(
    OperationType.DOWNLOAD,
    total_count=100,
    description="Downloading files"
)

# Update progress
monitor.update_progress(
    OperationType.DOWNLOAD,
    completed=10,
    failed=2,
    bytes_processed=1024000
)

# Report issues
monitor.report_error(
    OperationType.DOWNLOAD,
    "Download failed",
    metadata={"file": "document.pdf"}
)

# Complete operation
monitor.complete_operation(OperationType.DOWNLOAD)

# Get metrics
metrics = monitor.get_metrics(OperationType.DOWNLOAD)
print(f"Success rate: {metrics['success_rate']:.1f}%")

# Export report
monitor.export_report(Path("./reports/monitoring.json"))
```

### 5. Pipeline Orchestrator (`scripts/pipeline_orchestrator.py`)

Unified orchestrator that coordinates all components.

**Usage:**
```bash
# Run complete pipeline
python scripts/pipeline_orchestrator.py \
    --base-dir ./epstein_pipeline \
    --dashboard

# Run with configuration file
python scripts/pipeline_orchestrator.py \
    --config config.json

# Skip specific phases
python scripts/pipeline_orchestrator.py \
    --skip-download \
    --skip-ocr

# With authentication
python scripts/pipeline_orchestrator.py \
    --session-key "your_api_key"
```

**Python API:**
```python
from pathlib import Path
from scripts.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig

# Create configuration
config = PipelineConfig(
    base_dir=Path("./epstein_pipeline"),
    download_dir=Path("./epstein_pipeline/downloads"),
    organized_dir=Path("./epstein_pipeline/organized"),
    ocr_output_dir=Path("./epstein_pipeline/ocr_output"),
    log_dir=Path("./epstein_pipeline/logs"),
    max_concurrent_downloads=3,
    max_ocr_workers=2,
    enable_dashboard=True,
)

# Create orchestrator
orchestrator = PipelineOrchestrator(config)

# Run complete pipeline
success = orchestrator.run_full_pipeline(
    skip_download=False,
    skip_organize=False,
    skip_ocr=False
)

print(f"Pipeline {'succeeded' if success else 'failed'}")
```

## Installation

### Prerequisites

```bash
# System dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    qpdf \
    ocrmypdf

# Python dependencies
pip install -r requirements.txt
```

### Required Python Packages

```
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.0
tqdm>=4.66
pydantic>=2.6
pdfminer.six>=20231228
aiohttp>=3.13.2
rich>=14.2.0
```

## Configuration

### Configuration File Format

Create a `config.json`:

```json
{
  "base_dir": "./epstein_pipeline",
  "download_dir": "./epstein_pipeline/downloads",
  "organized_dir": "./epstein_pipeline/organized",
  "ocr_output_dir": "./epstein_pipeline/ocr_output",
  "log_dir": "./epstein_pipeline/logs",
  "max_concurrent_downloads": 3,
  "download_chunk_size": 8388608,
  "enable_checksums": true,
  "enable_deduplication": true,
  "auto_extract_zips": true,
  "max_ocr_workers": 2,
  "ocr_quality_threshold": "ACCEPTABLE",
  "skip_existing_ocr": true,
  "tesseract_lang": "eng",
  "enable_dashboard": true,
  "enable_alerts": true,
  "user_agent": "Epstein-Project-Pipeline/2.0"
}
```

### Authentication Configuration

For authenticated downloads, you can provide:

1. **Cookies** (e.g., session cookies from browser)
2. **Session Key** (API key/token)
3. **Custom Headers**

```json
{
  "cookies": {
    "session": "your_session_cookie",
    "auth": "your_auth_cookie"
  },
  "session_key": "your_api_key",
  "headers": {
    "X-Custom-Header": "value"
  }
}
```

## Usage Examples

### Example 1: Download and Organize DOJ Files

```python
from pathlib import Path
from epstein.download_manager import DownloadManager, DownloadTask, DownloadSource
from epstein.file_organizer import FileOrganizer

# Setup
download_dir = Path("./downloads")
organized_dir = Path("./organized")

# Create managers
download_mgr = DownloadManager(output_dir=download_dir)
organizer = FileOrganizer(base_dir=download_dir, organized_dir=organized_dir)

# Add download tasks (example URLs)
tasks = [
    DownloadTask(
        url="https://www.justice.gov/epstein/doj-disclosures/dataset-1.zip",
        destination=download_dir / "dataset-1.zip",
        source=DownloadSource.DOJ_DISCLOSURES,
        name="DOJ Dataset 1"
    )
]

task_ids = download_mgr.add_batch_tasks(tasks)

# Download
results = download_mgr.download_batch(task_ids)

# Organize
stats = organizer.organize_directory(download_dir, source="doj_disclosures")
print(f"Organized {stats['success']} files")
```

### Example 2: OCR Processing with Quality Checks

```python
from pathlib import Path
from epstein.ocr_processor import OCRProcessor, OCRQuality

# Setup
ocr_output = Path("./ocr_output")

# Create processor
processor = OCRProcessor(
    output_dir=ocr_output,
    max_workers=4,
    quality_threshold=OCRQuality.GOOD,  # Higher quality threshold
    max_retries=3
)

# Find PDFs
pdf_files = list(Path("./organized").glob("**/*.pdf"))
print(f"Found {len(pdf_files)} PDFs to process")

# Add tasks
task_ids = processor.add_batch_tasks(pdf_files)

# Process with parallel execution
results = processor.process_batch(task_ids, parallel=True)

# Get statistics
stats = processor.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Quality distribution: {stats['quality_distribution']}")

# Export report
processor.export_report(Path("./reports/ocr_report.json"))
```

### Example 3: Complete Automated Pipeline

```bash
# Create configuration
cat > pipeline_config.json << EOF
{
  "base_dir": "./epstein_automated",
  "max_concurrent_downloads": 5,
  "max_ocr_workers": 4,
  "enable_dashboard": true,
  "enable_alerts": true,
  "ocr_quality_threshold": "GOOD"
}
EOF

# Run pipeline
python scripts/pipeline_orchestrator.py \
    --config pipeline_config.json \
    --dashboard

# Check results
ls -lh epstein_automated/organized/
ls -lh epstein_automated/ocr_output/
cat epstein_automated/logs/reports/monitoring_*.json
```

## Monitoring & Alerts

### Alert Levels

- **INFO**: Informational messages
- **WARNING**: Potential issues (slow operations, quality below threshold)
- **ERROR**: Operation failures
- **CRITICAL**: High failure rates, system issues

### Alert Thresholds

- **High Failure Rate**: >20% failures
- **Slow Operation**: >300 seconds average duration
- **High Error Count**: >10 errors

### Alert Callbacks

Register custom alert handlers:

```python
from epstein.operation_monitor import OperationMonitor, Alert, AlertLevel

def send_email_alert(alert: Alert):
    if alert.level == AlertLevel.CRITICAL:
        # Send email notification
        send_email(
            subject=f"CRITICAL: {alert.operation_type.value}",
            body=alert.message
        )

def send_slack_alert(alert: Alert):
    if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
        # Send Slack notification
        send_slack_message(
            channel="#alerts",
            text=f"[{alert.level.value}] {alert.message}"
        )

# Register callbacks
monitor = OperationMonitor(log_dir=Path("./logs"))
monitor.register_alert_callback(send_email_alert)
monitor.register_alert_callback(send_slack_alert)
```

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/test_enhanced_pipeline.py -v

# Run specific test class
pytest tests/test_enhanced_pipeline.py::TestDownloadManager -v

# Run with coverage
pytest tests/test_enhanced_pipeline.py --cov=epstein --cov-report=html
```

### Test Coverage

The test suite includes:
- **Unit tests** for each component
- **Integration tests** for workflow
- **Mock-based tests** for external dependencies
- **End-to-end tests** for complete pipeline

Target: **>90% code coverage** for critical paths

## Troubleshooting

### Common Issues

#### 1. OCR Dependencies Missing

**Symptom**: `ocrmypdf` or `tesseract` not found

**Solution**:
```bash
sudo apt-get install -y tesseract-ocr ocrmypdf ghostscript qpdf
```

#### 2. Download Failures

**Symptom**: High download failure rate

**Solutions**:
- Check network connectivity
- Verify authentication (cookies/keys)
- Increase retry count
- Reduce concurrent downloads
- Check source URLs are valid

#### 3. Memory Issues During OCR

**Symptom**: Out of memory errors

**Solutions**:
- Reduce `max_ocr_workers`
- Process files in smaller batches
- Increase system memory
- Use `skip_existing_ocr=True`

#### 4. Slow Performance

**Symptom**: Pipeline takes too long

**Solutions**:
- Increase `max_concurrent_downloads`
- Increase `max_ocr_workers`
- Use SSD for storage
- Enable `skip_existing_ocr`
- Check network bandwidth

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Logs

```bash
# View audit trail
cat epstein_pipeline/logs/operation_audit.jsonl | jq .

# View alerts
cat epstein_pipeline/logs/alerts.jsonl | jq .

# View metrics
cat epstein_pipeline/logs/operation_metrics.json | jq .

# View download manifest
cat epstein_pipeline/downloads/download_manifest.jsonl | jq .
```

## Performance Optimization

### Recommended Settings

#### For Fast Downloads
```python
config = PipelineConfig(
    max_concurrent_downloads=10,
    download_chunk_size=16 * 1024 * 1024,  # 16MB chunks
    enable_checksums=False,  # Skip for speed (not recommended)
)
```

#### For High-Quality OCR
```python
config = PipelineConfig(
    max_ocr_workers=8,  # Use more cores
    ocr_quality_threshold=OCRQuality.EXCELLENT,
    max_retries=5,
)
```

#### For Resource-Constrained Systems
```python
config = PipelineConfig(
    max_concurrent_downloads=1,
    max_ocr_workers=1,
    download_chunk_size=4 * 1024 * 1024,  # 4MB chunks
)
```

## Security Considerations

1. **Authentication**: Store credentials securely (use environment variables or secret management)
2. **Zip Slip Protection**: Automatically applied during extraction
3. **File Validation**: Checksum verification enabled by default
4. **No Execution**: Downloaded content is never executed
5. **Audit Trail**: All operations are logged for accountability

## Integration with Existing Code

The new automation system integrates with existing Epstein project components:

- **Uses existing `scripts/epstein_bulk_downloader.py`** for DOJ/FBI/House downloads
- **Compatible with existing OCR pipeline** in `epstein/epstein_files_pipeline.py`
- **Works with existing agents** (can be orchestrated via agents)
- **Integrates with existing monitoring** (OpenTelemetry support)

## Roadmap

### Future Enhancements

1. **AI Agent Integration**
   - Download orchestration agent
   - OCR quality assessment agent
   - Automated error recovery

2. **Advanced Features**
   - Distributed processing
   - Cloud storage integration
   - Real-time web dashboard
   - Email/Slack notifications

3. **Performance Improvements**
   - GPU-accelerated OCR
   - Streaming decompression
   - Incremental updates

## Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

See repository license.

## Support

For issues or questions:
- Check troubleshooting section
- Review logs and reports
- Create GitHub issue with details

---

**Version**: 2.0.0  
**Last Updated**: 2026-02-13  
**Maintainer**: Epstein Project Team
