#!/usr/bin/env python3
"""monitor_downloads.py

Monitor download progress for epstein_bulk_downloader.py using tqdm progress bars.

Usage:
    python monitor_downloads.py [output_dir]

Args:
    output_dir: Path to epstein_project directory (default: ./epstein_project)

Displays live progress bars for each downloading ZIP file, showing current size,
download rate, and estimated time remaining (if total size known).
"""

import argparse
import time
from pathlib import Path
from typing import Dict, Optional

import tqdm

def get_file_sizes(directory: Path) -> Dict[str, int]:
    """Get current sizes of all ZIP files in directory."""
    sizes = {}
    for zip_file in directory.glob("*.zip"):
        try:
            sizes[zip_file.name] = zip_file.stat().st_size
        except OSError:
            continue
    return sizes

def format_size(size_bytes: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return ".1f"
        size_bytes /= 1024.0
    return ".1f"

def monitor_downloads(output_dir: Path, interval: float = 2.0) -> None:
    """Monitor download progress with tqdm bars."""
    zip_dir = output_dir / "raw" / "doj_disclosures" / "zips"
    zip_dir.mkdir(parents=True, exist_ok=True)

    print(f"Monitoring downloads in: {zip_dir}")
    print("Press Ctrl+C to stop monitoring\n")

    # Track previous sizes for rate calculation
    prev_sizes: Dict[str, int] = {}
    prev_time = time.time()
    progress_bars: Dict[str, tqdm.tqdm] = {}

    try:
        while True:
            current_sizes = get_file_sizes(zip_dir)
            current_time = time.time()
            time_diff = current_time - prev_time

            # Update or create progress bars
            for filename, size in current_sizes.items():
                if filename not in progress_bars:
                    # New file - create progress bar
                    progress_bars[filename] = tqdm.tqdm(
                        desc=f"{filename}",
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        ncols=100,
                        bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
                    )
                    prev_sizes[filename] = 0
                else:
                    # Existing file - update progress
                    prev_size = prev_sizes.get(filename, 0)
                    size_diff = size - prev_size

                    if time_diff > 0 and size_diff > 0:
                        rate = size_diff / time_diff
                        progress_bars[filename].update(size_diff)
                        # Update description with rate
                        progress_bars[filename].set_description(f"{filename} ({format_size(int(rate))}/s)")

            # Remove bars for completed/deleted files
            for filename in list(progress_bars.keys()):
                if filename not in current_sizes:
                    progress_bars[filename].close()
                    del progress_bars[filename]

            prev_sizes = current_sizes.copy()
            prev_time = current_time
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        for bar in progress_bars.values():
            bar.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor epstein_bulk_downloader progress")
    parser.add_argument("output_dir", nargs='?', default="./epstein_project",
                       help="Output directory to monitor (default: ./epstein_project)")
    parser.add_argument("--interval", type=float, default=2.0,
                       help="Update interval in seconds (default: 2.0)")

    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()

    if not output_dir.exists():
        print(f"Output directory {output_dir} does not exist. Is the downloader running?")
        return

    monitor_downloads(output_dir, args.interval)

if __name__ == "__main__":
    main()
