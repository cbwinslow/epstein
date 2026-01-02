#!/usr/bin/env python3
"""Summarize the OCR processing_status.jsonl into a concise JSON summary.

Writes output to `epstein_project/ocr_summary.json` with fields:
- total, counts by status, rates, avg before/after chars, top failures
"""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / 'epstein_project' / 'processing_status.jsonl'
OUT_FILE = ROOT / 'epstein_project' / 'ocr_summary.json'


def read_last_n(path: Path, n: int = 5000):
    if not path.exists():
        return []
    # simple read all, ok for typical sizes (we keep it simple)
    with path.open('r', encoding='utf-8') as fh:
        lines = [l.strip() for l in fh if l.strip()]
    return [json.loads(l) for l in lines[-n:]]


def summarize(entries):
    total = len(entries)
    counts = Counter()
    before_sum = 0
    after_sum = 0
    fallback_sum = 0
    failures = []
    for e in entries:
        st = e.get('ocr_status') or 'unknown'
        counts[st] += 1
        if e.get('fallback_status'):
            counts['fallback_' + e.get('fallback_status')] += 1
        before_sum += e.get('before_chars', 0)
        after_sum += e.get('after_chars', 0)
        fallback_sum += e.get('fallback_chars', 0)
        if st != 'ok':
            failures.append({'sha256': e.get('sha256'), 'ocr_status': st, 'error': e.get('error'), 'log': e.get('log')})
    avg_before = before_sum / total if total else 0
    avg_after = after_sum / total if total else 0
    avg_fallback = fallback_sum / total if total else 0
    failure_rate = (counts['ocr_failed'] + counts['ocr_empty']) / total if total else 0

    summary = {
        'total': total,
        'counts': dict(counts),
        'avg_before_chars': avg_before,
        'avg_after_chars': avg_after,
        'avg_fallback_chars': avg_fallback,
        'failure_rate': failure_rate,
        'top_failures': failures[:10]
    }
    return summary


def main():
    entries = read_last_n(STATUS_FILE)
    summary = summarize(entries)
    OUT_FILE.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Wrote', OUT_FILE)


if __name__ == '__main__':
    main()
