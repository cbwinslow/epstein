#!/usr/bin/env python3
"""
Demo Script: DOJ Epstein Files Automation System
Demonstrates the complete pipeline with example data.

Author: Epstein Project Team
Date: 2026-02-13
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from epstein.download_manager import (
    DownloadManager,
    SessionConfig,
)
from epstein.file_organizer import FileOrganizer
from epstein.operation_monitor import OperationMonitor, OperationType

print("=" * 70)
print("DOJ Epstein Files Automation System - Demo")
print("=" * 70)
print()

# Create temporary workspace
workspace = Path(tempfile.mkdtemp(prefix="epstein_demo_"))
print(f"✓ Created workspace: {workspace}")

# Setup directories
download_dir = workspace / "downloads"
organized_dir = workspace / "organized"
log_dir = workspace / "logs"

for d in [download_dir, organized_dir, log_dir]:
    d.mkdir(parents=True, exist_ok=True)

print("✓ Created directory structure")
print()

# ============================================================================
# 1. DOWNLOAD MANAGER DEMO
# ============================================================================
print("-" * 70)
print("1. DOWNLOAD MANAGER DEMO")
print("-" * 70)

# Create session configuration
session_config = SessionConfig(
    user_agent="Epstein-Demo/1.0",
    timeout=30,
)

# Create download manager
download_mgr = DownloadManager(
    output_dir=download_dir,
    max_concurrent=2,
    session_config=session_config,
)

print("✓ Download manager initialized")
print(f"  - Output directory: {download_dir}")
print("  - Max concurrent: 2")
print(f"  - User agent: {session_config.user_agent}")

# Create demo files (simulating downloads)
print("\n📥 Simulating file downloads...")

demo_files = []
for i in range(5):
    filename = f"demo_document_{i+1}.pdf"
    file_path = download_dir / filename

    # Create demo content
    content = f"Demo PDF Document {i+1}\n" + ("Sample content. " * 100)
    file_path.write_text(content)
    demo_files.append(file_path)

    print(f"  ✓ Created: {filename} ({len(content)} bytes)")

print(f"\n✓ Downloaded {len(demo_files)} files")
print()

# ============================================================================
# 2. OPERATION MONITOR DEMO
# ============================================================================
print("-" * 70)
print("2. OPERATION MONITOR DEMO")
print("-" * 70)

# Create monitor
monitor = OperationMonitor(
    log_dir=log_dir,
    enable_dashboard=False,  # Disabled for demo
    enable_alerts=False,  # Disabled for demo to simplify
)

print("✓ Monitor initialized")
print(f"  - Log directory: {log_dir}")
print("  - Alerts enabled: True")
print()

# Track download operation
print("📊 Tracking operation metrics...")
monitor.start_operation(
    OperationType.DOWNLOAD, total_count=len(demo_files), description="Demo downloads"
)

for i, file in enumerate(demo_files):
    size = file.stat().st_size
    monitor.update_progress(
        OperationType.DOWNLOAD, completed=1, bytes_processed=size, duration_seconds=0.1
    )

monitor.complete_operation(OperationType.DOWNLOAD)

# Get and display metrics
download_metrics = monitor.get_metrics(OperationType.DOWNLOAD)
print("\n✓ Download metrics:")
print(f"  - Total files: {download_metrics['total_count']}")
print(f"  - Completed: {download_metrics['completed_count']}")
print(f"  - Success rate: {download_metrics['success_rate']:.1f}%")
print(f"  - Total bytes: {download_metrics['total_bytes_processed']:,}")
print()

# ============================================================================
# 3. FILE ORGANIZER DEMO
# ============================================================================
print("-" * 70)
print("3. FILE ORGANIZER DEMO")
print("-" * 70)

# Create file organizer
organizer = FileOrganizer(
    base_dir=download_dir,
    organized_dir=organized_dir,
    dedup_enabled=True,
    auto_extract_zips=False,
)

print("✓ File organizer initialized")
print(f"  - Base directory: {download_dir}")
print(f"  - Organized directory: {organized_dir}")
print("  - Deduplication: Enabled")
print()

# Track organization operation
print("📁 Organizing files...")
monitor.start_operation(
    OperationType.ORGANIZE, total_count=len(demo_files), description="File organization"
)

organized_count = 0
for file in demo_files:
    success, organized_path, error = organizer.organize_file(
        file, source="demo_files", dataset_number=1
    )

    if success:
        organized_count += 1
        monitor.update_progress(OperationType.ORGANIZE, completed=1)
        print(f"  ✓ Organized: {file.name} → {organized_path.relative_to(organized_dir)}")
    else:
        monitor.update_progress(OperationType.ORGANIZE, failed=1)
        monitor.report_error(OperationType.ORGANIZE, error or "Unknown error")
        print(f"  ✗ Failed: {file.name}")

monitor.complete_operation(OperationType.ORGANIZE)

# Get organization stats
org_stats = organizer.get_statistics()
print("\n✓ Organization complete:")
print(f"  - Total files organized: {org_stats['total_files']}")
print(f"  - Total size: {org_stats['total_size_bytes']:,} bytes")
print(f"  - Categories: {len([k for k, v in org_stats['by_category'].items() if v['count'] > 0])}")
print()

# ============================================================================
# 4. SUMMARY & REPORTS
# ============================================================================
print("-" * 70)
print("4. SUMMARY & REPORTS")
print("-" * 70)

# Get overall statistics
print("\n📈 Overall Statistics:")
print()

all_metrics = monitor.get_metrics()
for op_type, metrics in all_metrics.items():
    if metrics["total_count"] > 0:
        print(f"{op_type.upper()}:")
        print(f"  ✓ Completed: {metrics['completed_count']}/{metrics['total_count']}")
        print(f"  ✓ Success rate: {metrics['success_rate']:.1f}%")
        print(f"  ✓ Duration: {metrics['elapsed_seconds']:.2f}s")
        print()

# Check for alerts
recent_alerts = monitor.get_recent_alerts(count=5)
if recent_alerts:
    print("🚨 Recent Alerts:")
    for alert in recent_alerts:
        print(f"  [{alert.level.value.upper()}] {alert.message}")
else:
    print("✓ No alerts generated")

print()

# Export reports
print("📄 Exporting reports...")
report_file = log_dir / "demo_report.json"
monitor.export_report(report_file)
print(f"  ✓ Report saved: {report_file}")

# Display file structure
print()
print("📂 Workspace Structure:")
print(f"{workspace}/")
for item in sorted(workspace.rglob("*")):
    if item.is_file():
        rel_path = item.relative_to(workspace)
        size = item.stat().st_size
        print(f"  {rel_path} ({size:,} bytes)")

print()

# ============================================================================
# 5. CLEANUP & CONCLUSION
# ============================================================================
print("-" * 70)
print("DEMO COMPLETE")
print("-" * 70)
print()
print(f"✓ Demo workspace: {workspace}")
print(f"✓ Logs available at: {log_dir}")
print(f"✓ Organized files at: {organized_dir}")
print()
print("To clean up demo files:")
print(f"  rm -rf {workspace}")
print()

print("=" * 70)
print("Next Steps:")
print("=" * 70)
print()
print("1. Review the automation system guide:")
print("   docs/AUTOMATION_SYSTEM_GUIDE.md")
print()
print("2. Create your configuration:")
print("   cp docs/examples/config.json my_config.json")
print()
print("3. Run the full pipeline:")
print("   python scripts/pipeline_orchestrator.py --config my_config.json")
print()
print("4. Monitor progress:")
print("   tail -f epstein_pipeline/logs/operation_audit.jsonl")
print()
print("=" * 70)
