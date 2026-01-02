import json
from pathlib import Path
from agents.pipeline_monitor import PipelineMonitor


def test_ingest_processing_status(tmp_path):
    # create a fake processing_status.jsonl with various outcomes
    entries = [
        {'sha256': 'a', 'ocr_status': 'ok', 'before_chars': 0, 'after_chars': 500},
        {'sha256': 'b', 'ocr_status': 'ocr_failed', 'before_chars': 0, 'after_chars': 0, 'error': 'timeout'},
        {'sha256': 'c', 'ocr_status': 'ocr_empty', 'before_chars': 0, 'after_chars': 0, 'fallback_status': 'fallback_empty'}
    ]
    p = tmp_path / 'processing_status.jsonl'
    with p.open('w') as fh:
        for e in entries:
            fh.write(json.dumps(e) + '\n')

    pm = PipelineMonitor()
    summary = pm.ingest_processing_status(str(p), window=10)
    assert summary['total'] == 3
    assert summary['counts']['ok'] == 1
    assert summary['counts']['ocr_failed'] == 1
    assert summary['counts']['ocr_empty'] == 1
    # check alerts were emitted
    assert any('OCR failure rate' in a['msg'] for a in pm.alerts) or any('empty+fallback_empty' in a['msg'] for a in pm.alerts)
