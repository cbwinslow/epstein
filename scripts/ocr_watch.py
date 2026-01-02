#!/usr/bin/env python3
"""OCR Watcher: run summary, ingest into PipelineMonitor, and emit alerts.

Usage: python3 scripts/ocr_watch.py

Optional env vars:
- EPSTEIN_ROOT_OVERRIDE: override repo root (used in tests)
- OCR_STATUS_PATH: path to processing_status.jsonl (default: epstein_project/processing_status.jsonl)
- OCR_SUMMARY_OUT: path to write summary JSON (default: epstein_project/ocr_summary.json)
"""
import json
import logging
import os
from pathlib import Path
from agents.pipeline_monitor import PipelineMonitor
import scripts.ocr_summary as ocr_summary

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
ROOT = Path(os.environ.get('EPSTEIN_ROOT_OVERRIDE') or Path(__file__).resolve().parents[1])
STATUS_PATH = Path(os.environ.get('OCR_STATUS_PATH') or ROOT / 'epstein_project' / 'processing_status.jsonl')
OUT_PATH = Path(os.environ.get('OCR_SUMMARY_OUT') or ROOT / 'epstein_project' / 'ocr_summary.json')


def run_once(status_path: Path = STATUS_PATH, out_path: Path = OUT_PATH):
    pm = PipelineMonitor()
    logging.info('Reading status from %s', status_path)
    summary = pm.ingest_processing_status(str(status_path))
    if 'error' in summary:
        logging.error('Summary error: %s', summary['error'])
    else:
        out_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
        logging.info('Wrote summary to %s', out_path)

    if pm.alerts:
        logging.warning('Alerts: %s', json.dumps(pm.alerts, indent=2))
    else:
        logging.info('No alerts')
    # return for programmatic use
    return summary, pm.alerts


if __name__ == '__main__':
    run_once()
