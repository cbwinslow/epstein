# Tasks - DOJ Epstein Files Automation System

**Generated:** 2026-02-23  
**Based on:** Comprehensive validation and assessment  
**Priority Levels:** 🔴 Critical | 🟡 Important | 🟢 Nice to Have

---

## 🔴 Critical Priority Tasks

### TASK-001: Fix Rich Dashboard Hanging Issue
**Status:** 🔴 Open  
**Component:** Operation Monitor  
**Issue:** Dashboard causes hang when enabled  
**Impact:** Cannot use optional dashboard feature  

**Steps to Fix:**
1. Review `epstein/operation_monitor.py` lines 450-475 (dashboard_loop function)
2. Add timeout mechanism to Live context manager
3. Implement error handling for dashboard thread
4. Add graceful shutdown on exception
5. Test with `enable_dashboard=True`

**Code Location:**
```
File: epstein/operation_monitor.py
Function: start_dashboard() and dashboard_loop()
Lines: ~450-475
```

**Test Command:**
```bash
PYTHONPATH=/home/runner/work/epstein/epstein python -c "
from pathlib import Path
from epstein.operation_monitor import OperationMonitor, OperationType
import time

monitor = OperationMonitor(
    log_dir=Path('/tmp/test'),
    enable_dashboard=True
)
monitor.start_operation(OperationType.DOWNLOAD, total_count=10)
time.sleep(2)
monitor.stop_dashboard()
print('Dashboard test passed')
"
```

**Acceptance Criteria:**
- [ ] Dashboard starts without hanging
- [ ] Dashboard stops cleanly
- [ ] No thread leaks
- [ ] Error handling works
- [ ] Test passes within 5 seconds

---

### TASK-002: Add PYTHONPATH Configuration
**Status:** 🔴 Open  
**Component:** Setup & Installation  
**Issue:** Modules require PYTHONPATH to be set  
**Impact:** Users cannot run scripts without setup  

**Steps to Fix:**
1. Create `setup_environment.sh` script
2. Add PYTHONPATH export to script
3. Update documentation with setup instructions
4. Add to quickstart guide
5. Test on clean environment

**Create File:** `scripts/setup_environment.sh`
```bash
#!/bin/bash
# Setup environment for Epstein automation system

export PYTHONPATH="/home/runner/work/epstein/epstein:$PYTHONPATH"
echo "✓ PYTHONPATH configured"
echo "✓ Run scripts with: python scripts/pipeline_orchestrator.py"
```

**Update Files:**
- `docs/AUTOMATION_QUICK_START.md` - Add setup step
- `docs/AUTOMATION_SYSTEM_GUIDE.md` - Add environment section
- `README.md` - Add setup instructions

**Test Command:**
```bash
# Without setup (should fail)
python -c "from epstein.download_manager import DownloadManager"

# After setup (should work)
source scripts/setup_environment.sh
python -c "from epstein.download_manager import DownloadManager; print('✓ Import works')"
```

**Acceptance Criteria:**
- [ ] Setup script created
- [ ] Documentation updated
- [ ] Test passes on fresh environment
- [ ] Instructions are clear

---

### TASK-003: Create Installation Script for OCR Dependencies
**Status:** 🔴 Open  
**Component:** OCR Processor  
**Issue:** OCR dependencies not installed  
**Impact:** OCR features cannot be used  

**Steps to Fix:**
1. Create `scripts/install_ocr_deps.sh`
2. Add platform detection (Ubuntu/Debian/etc)
3. Add dependency check function
4. Install packages with appropriate package manager
5. Verify installation
6. Document usage

**Create File:** `scripts/install_ocr_deps.sh`
```bash
#!/bin/bash
# Install OCR dependencies for Epstein automation system

echo "Installing OCR dependencies..."

# Detect OS
if [ -f /etc/debian_version ]; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr ocrmypdf ghostscript qpdf
elif [ -f /etc/redhat-release ]; then
    # RHEL/CentOS/Fedora
    sudo yum install -y tesseract ocrmypdf ghostscript qpdf
elif [ "$(uname)" == "Darwin" ]; then
    # macOS
    brew install tesseract ocrmypdf ghostscript qpdf
else
    echo "❌ Unsupported OS. Please install manually:"
    echo "   - tesseract-ocr"
    echo "   - ocrmypdf"
    echo "   - ghostscript"
    echo "   - qpdf"
    exit 1
fi

# Verify installation
echo "Verifying installation..."
for cmd in tesseract ocrmypdf gs qpdf; do
    if command -v $cmd &> /dev/null; then
        echo "✓ $cmd installed"
    else
        echo "❌ $cmd not found"
    fi
done

echo "✓ OCR dependencies installation complete"
```

**Test Command:**
```bash
bash scripts/install_ocr_deps.sh
python -c "from epstein.ocr_processor import OCRProcessor; OCRProcessor(Path('/tmp/test'))"
```

**Acceptance Criteria:**
- [ ] Script created and executable
- [ ] Works on Ubuntu/Debian
- [ ] Verifies installation
- [ ] Clear error messages
- [ ] Documentation updated

---

## 🟡 Important Priority Tasks

### TASK-004: Add Example Configuration Files
**Status:** 🟡 Open  
**Component:** Configuration  
**Issue:** No example configs provided  
**Impact:** Users don't know how to configure system  

**Files to Create:**

**1. `configs/production.json`**
```json
{
  "base_dir": "./epstein_production",
  "max_concurrent_downloads": 5,
  "max_ocr_workers": 4,
  "ocr_quality_threshold": "GOOD",
  "enable_checksums": true,
  "enable_deduplication": true,
  "auto_extract_zips": true,
  "enable_dashboard": false,
  "enable_alerts": true,
  "user_agent": "Epstein-Production/2.0"
}
```

**2. `configs/development.json`**
```json
{
  "base_dir": "./epstein_dev",
  "max_concurrent_downloads": 2,
  "max_ocr_workers": 1,
  "ocr_quality_threshold": "ACCEPTABLE",
  "enable_checksums": true,
  "enable_deduplication": true,
  "auto_extract_zips": true,
  "enable_dashboard": false,
  "enable_alerts": true,
  "user_agent": "Epstein-Dev/2.0"
}
```

**3. `configs/testing.json`**
```json
{
  "base_dir": "/tmp/epstein_test",
  "max_concurrent_downloads": 1,
  "max_ocr_workers": 1,
  "ocr_quality_threshold": "ACCEPTABLE",
  "enable_checksums": false,
  "enable_deduplication": false,
  "auto_extract_zips": false,
  "enable_dashboard": false,
  "enable_alerts": false,
  "user_agent": "Epstein-Test/2.0"
}
```

**Test Command:**
```bash
python scripts/pipeline_orchestrator.py --config configs/development.json --skip-download --skip-ocr
```

**Acceptance Criteria:**
- [ ] 3 config files created
- [ ] Configs are valid JSON
- [ ] Pipeline accepts configs
- [ ] Documentation mentions configs

---

### TASK-005: Create Real-World Usage Examples
**Status:** 🟡 Open  
**Component:** Documentation & Examples  
**Issue:** No practical usage examples  
**Impact:** Users don't know how to use system  

**Files to Create:**

**1. `examples/download_doj_files.py`**
```python
#!/usr/bin/env python3
"""
Example: Download DOJ Epstein files

Shows how to:
- Configure download manager
- Add DOJ download tasks
- Monitor progress
- Handle errors
"""
# Implementation needed
```

**2. `examples/organize_downloaded_files.py`**
```python
#!/usr/bin/env python3
"""
Example: Organize downloaded files

Shows how to:
- Initialize file organizer
- Organize by source type
- Handle deduplication
- Generate reports
"""
# Implementation needed
```

**3. `examples/ocr_processing.py`**
```python
#!/usr/bin/env python3
"""
Example: OCR process PDFs

Shows how to:
- Set up OCR processor
- Process batch of PDFs
- Validate quality
- Export results
"""
# Implementation needed
```

**4. `examples/full_workflow.py`**
```python
#!/usr/bin/env python3
"""
Example: Complete workflow

Shows complete automation:
- Download files
- Organize them
- Run OCR
- Monitor progress
- Generate reports
"""
# Implementation needed
```

**Acceptance Criteria:**
- [ ] 4 example scripts created
- [ ] All scripts are executable
- [ ] Scripts include documentation
- [ ] Scripts run without errors
- [ ] Added to documentation index

---

### TASK-006: Enhance Validation Script
**Status:** 🟡 Open  
**Component:** Testing  
**Issue:** Validation script hangs on integration test  
**Impact:** Cannot run full automated validation  

**Steps to Fix:**
1. Fix hanging issue in integration test
2. Add timeout to all tests
3. Make dashboard test optional
4. Generate JSON report at end
5. Add --quick mode for CI/CD

**Update File:** `scripts/validate_automation_system.py`

**Changes Needed:**
- Line ~400: Add timeout wrapper
- Line ~450: Skip dashboard test or add timeout
- Line ~500: Generate JSON report on hang
- Add command line arguments

**Test Command:**
```bash
PYTHONPATH=/home/runner/work/epstein/epstein timeout 120 python scripts/validate_automation_system.py --quick
cat /tmp/validation_report.json
```

**Acceptance Criteria:**
- [ ] Script completes within 60 seconds
- [ ] JSON report generated
- [ ] All tests run
- [ ] --quick mode available
- [ ] Exit code indicates success/failure

---

### TASK-007: Add CI/CD GitHub Actions Workflow
**Status:** 🟡 Open  
**Component:** CI/CD  
**Issue:** No automated testing in CI  
**Impact:** Changes not validated automatically  

**Create File:** `.github/workflows/automation-tests.yml`
```yaml
name: Automation System Tests

on:
  push:
    branches: [ main, develop, copilot/* ]
    paths:
      - 'epstein/download_manager.py'
      - 'epstein/file_organizer.py'
      - 'epstein/ocr_processor.py'
      - 'epstein/operation_monitor.py'
      - 'scripts/pipeline_orchestrator.py'
      - 'scripts/validate_automation_system.py'
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install requests pdfminer.six tqdm rich
      
      - name: Run validation
        run: |
          export PYTHONPATH=$PWD:$PYTHONPATH
          timeout 120 python scripts/validate_automation_system.py --quick
      
      - name: Upload validation report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: validation-report
          path: /tmp/validation_report.*
```

**Acceptance Criteria:**
- [ ] Workflow file created
- [ ] Runs on push to main branches
- [ ] Validates automation system
- [ ] Uploads artifacts
- [ ] Completes in < 5 minutes

---

## 🟢 Nice to Have Tasks

### TASK-008: Add Performance Benchmarking
**Status:** 🟢 Open  
**Component:** Performance  
**Priority:** Low  

**Create File:** `scripts/benchmark_automation_system.py`

**Benchmarks to Add:**
- Download speed (various file sizes)
- File organization speed
- OCR processing speed
- Monitoring overhead
- Memory usage

**Acceptance Criteria:**
- [ ] Benchmark script created
- [ ] Tests various scenarios
- [ ] Generates performance report
- [ ] Establishes baselines

---

### TASK-009: Add Prometheus Metrics Export
**Status:** 🟢 Open  
**Component:** Monitoring  
**Priority:** Low  

**Changes:**
- Add prometheus_client dependency
- Export metrics from OperationMonitor
- Create metrics endpoint
- Document setup

**Acceptance Criteria:**
- [ ] Metrics exported
- [ ] Endpoint documented
- [ ] Example queries provided

---

### TASK-010: Create Web Dashboard
**Status:** 🟢 Open  
**Component:** UI  
**Priority:** Low  

**Features:**
- Real-time progress visualization
- Download status
- OCR progress
- Error logs
- Metrics charts

**Tech Stack:**
- Backend: FastAPI
- Frontend: React or vanilla JS
- Charts: Chart.js or D3

**Acceptance Criteria:**
- [ ] Web UI functional
- [ ] Real-time updates
- [ ] Mobile responsive
- [ ] Documentation provided

---

## Testing Checklist

Before marking tasks complete, verify:

### Unit Tests
- [ ] Component initializes correctly
- [ ] Methods work as expected
- [ ] Error handling works
- [ ] Edge cases covered

### Integration Tests
- [ ] Components work together
- [ ] Data flows correctly
- [ ] No memory leaks
- [ ] Cleanup works

### Manual Tests
- [ ] Run real workflow
- [ ] Check logs
- [ ] Verify outputs
- [ ] Test error scenarios

### Documentation
- [ ] Code documented
- [ ] User guide updated
- [ ] API docs current
- [ ] Examples work

---

## Quick Reference Commands

### Run Validation
```bash
export PYTHONPATH=$PWD:$PYTHONPATH
python scripts/validate_automation_system.py
```

### Run Pipeline
```bash
export PYTHONPATH=$PWD:$PYTHONPATH
python scripts/pipeline_orchestrator.py --config configs/development.json
```

### Run Tests
```bash
pytest tests/test_enhanced_pipeline.py -v
```

### Check Dependencies
```bash
python -c "
from epstein.download_manager import DownloadManager
from epstein.file_organizer import FileOrganizer
from epstein.ocr_processor import OCRProcessor
from epstein.operation_monitor import OperationMonitor
print('✓ All modules import successfully')
"
```

---

## Notes

### Known Issues
1. Rich dashboard can hang - disable with `enable_dashboard=False`
2. PYTHONPATH must be set for imports
3. OCR dependencies require system packages

### Environment Setup
```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/epstein:$PYTHONPATH

# Install Python dependencies
pip install requests pdfminer.six tqdm rich

# Install OCR dependencies (Ubuntu)
sudo apt-get install tesseract-ocr ocrmypdf ghostscript qpdf
```

### Getting Help
- See `VALIDATION_REPORT.md` for assessment details
- See `docs/AUTOMATION_SYSTEM_GUIDE.md` for complete guide
- See `docs/AUTOMATION_QUICK_START.md` for quick start

---

**Last Updated:** 2026-02-23  
**Total Tasks:** 10 (3 Critical, 4 Important, 3 Nice to Have)  
**Completion:** 0% (0/10 complete)
