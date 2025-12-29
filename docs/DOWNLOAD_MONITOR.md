# Download Monitor Tool

A real-time progress monitoring tool for the Epstein bulk downloader using tqdm progress bars.

## Overview

The `monitor_downloads.py` script provides live visualization of download progress for the `epstein_bulk_downloader.py` script. It displays progress bars with current download sizes, rates, and time estimates.

## Features

- **Real-time progress bars** for each downloading ZIP file
- **Download rate calculation** (KB/s, MB/s)
- **Automatic detection** of new/removed files
- **Non-intrusive monitoring** - runs alongside the downloader
- **Keyboard interrupt** to stop monitoring gracefully

## Usage

### Basic Usage

```bash
python monitor_downloads.py
```

This monitors the default output directory `./epstein_project`.

### Custom Output Directory

```bash
python monitor_downloads.py /path/to/epstein_project
```

### Options

- `--interval`: Update interval in seconds (default: 2.0)
- `--help`: Show help message

### Example

```bash
# Monitor with 1-second updates
python monitor_downloads.py --interval 1.0

# Monitor custom directory
python monitor_downloads.py /home/user/downloads/epstein_project
```

## Output

The monitor displays progress bars like:

```
Monitoring downloads in: /home/user/epstein_project/raw/doj_disclosures/zips
Press Ctrl+C to stop monitoring

doj_dataset_01.zip (542KB/s):   0%|██████████████| 80.0M/? [02:28<?, ?B/s]
doj_dataset_02.zip (369KB/s):   0%|█████████████| 64.0M/? [02:38<?, ?B/s]
doj_dataset_03.zip (364KB/s):   0%|█████████████| 56.0M/? [02:36<?, ?B/s]
```

## How It Works

1. **File Size Tracking**: Periodically scans the ZIP directory for file sizes
2. **Rate Calculation**: Computes download speed based on size differences over time
3. **Progress Bars**: Uses tqdm to display live progress with rates and elapsed time
4. **Dynamic Updates**: Adds/removes bars as files appear/disappear

## Integration with Downloader

Run both scripts simultaneously:

```bash
# Terminal 1: Start the downloader
python epstein_bulk_downloader.py --sources doj

# Terminal 2: Monitor progress
python monitor_downloads.py
```

## Requirements

- Python 3.8+
- tqdm library (`pip install tqdm`)
- Access to the output directory being monitored

## Troubleshooting

- **No progress bars appear**: Check if the output directory exists and contains downloading ZIP files
- **Permission errors**: Ensure read access to the ZIP files
- **High CPU usage**: Increase the `--interval` value

## Checkpoint: Current Progress

As of 2025-12-29 01:57:

- **Active Downloads**: 3 DOJ dataset ZIP files
- **Total Downloaded**: ~208MB
- **Current Rates**: ~350-540KB/s per file
- **Status**: Downloads progressing slowly but steadily
- **Estimated Completion**: Hours to days depending on file sizes

Files being downloaded:
- doj_dataset_01.zip: 88MB @ 537KB/s
- doj_dataset_02.zip: 64MB @ 369KB/s
- doj_dataset_03.zip: 56MB @ 364KB/s
