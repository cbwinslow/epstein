# DOJ Epstein Files Automation System - Quick Start

## 🎯 What Is This?

A complete, production-ready automation system for downloading, organizing, and processing Epstein-related documents from government sources (DOJ, FBI, House Oversight, GovInfo).

## ⚡ Quick Start (5 Minutes)

### 1. View Demo
```bash
cd /home/runner/work/epstein/epstein
python examples/demo_automation_system.py
```

### 2. Read Documentation
```bash
# Complete guide
cat docs/AUTOMATION_SYSTEM_GUIDE.md

# Technical summary
cat docs/IMPLEMENTATION_SUMMARY.md
```

### 3. Run Your First Pipeline
```bash
# Create config
cat > my_config.json << EOF
{
  "base_dir": "./my_pipeline",
  "max_concurrent_downloads": 3,
  "max_ocr_workers": 2,
  "enable_dashboard": false
}
EOF

# Run pipeline
python scripts/pipeline_orchestrator.py --config my_config.json
```

## 📦 What's Included

### Core Components
1. **Download Manager** - Automated downloads with auth
2. **File Organizer** - Smart organization & deduplication
3. **OCR Processor** - Quality-validated OCR
4. **Operation Monitor** - Real-time tracking & alerts
5. **Pipeline Orchestrator** - Unified workflow

### Documentation
- `docs/AUTOMATION_SYSTEM_GUIDE.md` - Complete guide (800+ lines)
- `docs/IMPLEMENTATION_SUMMARY.md` - Technical overview
- `examples/demo_automation_system.py` - Working demo

### Testing
- `tests/test_enhanced_pipeline.py` - Comprehensive test suite (40+ tests)

## 🚀 Key Features

✅ **Session/Cookie Auth** - Download with your credentials  
✅ **Resumable Downloads** - Never lose progress  
✅ **Auto Organization** - Smart categorization & naming  
✅ **OCR Quality** - Validated text extraction  
✅ **Real-time Monitoring** - Track everything  
✅ **Error Handling** - Automatic retries & recovery  
✅ **Comprehensive Logging** - Audit trails for all operations  

## 📖 Usage Examples

### Example 1: Download & Organize
```python
from epstein.download_manager import DownloadManager, DownloadTask, DownloadSource
from epstein.file_organizer import FileOrganizer
from pathlib import Path

# Setup
dm = DownloadManager(output_dir=Path("./downloads"))
org = FileOrganizer(base_dir=Path("./downloads"), organized_dir=Path("./organized"))

# Add download
task = DownloadTask(
    url="https://example.com/file.pdf",
    destination=Path("./downloads/file.pdf"),
    source=DownloadSource.DOJ_DISCLOSURES,
    name="Sample"
)
task_id = dm.add_task(task)

# Download
dm.download_with_retry(task_id)

# Organize
org.organize_directory(Path("./downloads"), source="doj")
```

### Example 2: OCR Processing
```python
from epstein.ocr_processor import OCRProcessor, OCRQuality
from pathlib import Path

# Setup
ocr = OCRProcessor(
    output_dir=Path("./ocr_output"),
    max_workers=2,
    quality_threshold=OCRQuality.GOOD
)

# Add PDFs
pdfs = list(Path("./organized").glob("**/*.pdf"))
task_ids = ocr.add_batch_tasks(pdfs)

# Process
results = ocr.process_batch(task_ids, parallel=True)

# Get stats
stats = ocr.get_statistics()
print(f"Success: {stats['success_rate']:.1f}%")
```

### Example 3: Complete Pipeline
```python
from scripts.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig
from pathlib import Path

config = PipelineConfig(
    base_dir=Path("./pipeline"),
    max_concurrent_downloads=3,
    max_ocr_workers=2
)

orchestrator = PipelineOrchestrator(config)
success = orchestrator.run_full_pipeline()
```

## 🔧 Configuration

Create `config.json`:
```json
{
  "base_dir": "./epstein_pipeline",
  "max_concurrent_downloads": 3,
  "max_ocr_workers": 2,
  "ocr_quality_threshold": "GOOD",
  "enable_deduplication": true,
  "auto_extract_zips": true,
  "enable_alerts": true
}
```

## 📊 Monitoring

### Real-time Metrics
```python
from epstein.operation_monitor import OperationMonitor, OperationType

monitor = OperationMonitor(log_dir=Path("./logs"))
monitor.start_operation(OperationType.DOWNLOAD, total_count=100)

# ... do work ...

metrics = monitor.get_metrics(OperationType.DOWNLOAD)
print(f"Success: {metrics['success_rate']:.1f}%")
```

### View Logs
```bash
# Audit trail
cat logs/operation_audit.jsonl | jq .

# Metrics
cat logs/operation_metrics.json | jq .

# Alerts
cat logs/alerts.jsonl | jq .
```

## 🧪 Testing

```bash
# Run tests
pytest tests/test_enhanced_pipeline.py -v

# With coverage
pytest tests/test_enhanced_pipeline.py --cov=epstein --cov-report=html
```

## 🔒 Security

- ✅ Session/cookie auth
- ✅ Zip Slip protection
- ✅ Checksum verification
- ✅ No code execution
- ✅ Audit trails
- ✅ Secure credential handling

## 🐛 Troubleshooting

### Common Issues

**OCR dependencies missing?**
```bash
sudo apt-get install tesseract-ocr ocrmypdf ghostscript qpdf
```

**Downloads failing?**
- Check network connectivity
- Verify authentication
- Increase retry count
- Reduce concurrent downloads

**Memory issues?**
- Reduce `max_ocr_workers`
- Process in smaller batches
- Enable `skip_existing_ocr`

See `docs/AUTOMATION_SYSTEM_GUIDE.md` for detailed troubleshooting.

## 📁 File Structure

```
epstein/
├── epstein/
│   ├── download_manager.py      # Download automation
│   ├── file_organizer.py        # File organization
│   ├── ocr_processor.py          # OCR processing
│   └── operation_monitor.py      # Monitoring system
├── scripts/
│   └── pipeline_orchestrator.py  # Unified orchestrator
├── tests/
│   └── test_enhanced_pipeline.py # Test suite
├── docs/
│   ├── AUTOMATION_SYSTEM_GUIDE.md     # Complete guide
│   └── IMPLEMENTATION_SUMMARY.md       # Technical summary
└── examples/
    └── demo_automation_system.py       # Demo script
```

## 🎓 Documentation

1. **[Automation Guide](docs/AUTOMATION_SYSTEM_GUIDE.md)** - Complete documentation
2. **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - Technical details
3. **[Demo Script](examples/demo_automation_system.py)** - Working example

## 🤝 Integration

Works with existing code:
- ✅ `scripts/epstein_bulk_downloader.py`
- ✅ Existing OCR pipeline
- ✅ Existing agents
- ✅ Existing monitoring

## 📈 Performance

- **Download**: 3-10 concurrent (configurable)
- **OCR**: 1-8 parallel workers (configurable)
- **Organization**: Hash-based deduplication (O(1))
- **Monitoring**: Real-time metrics

## 🎯 Support

- **Documentation**: See `docs/AUTOMATION_SYSTEM_GUIDE.md`
- **Issues**: Check troubleshooting section
- **Examples**: See `examples/` directory

## 📝 License

See repository license.

---

## 🚀 Next Steps

1. ✅ Read documentation
2. ✅ Run demo
3. ✅ Create configuration
4. ✅ Run pipeline
5. ✅ Monitor results

---

**Version**: 2.0.0  
**Status**: Production Ready  
**Documentation**: Complete  
**Testing**: Framework Ready  
**Last Updated**: 2026-02-13
