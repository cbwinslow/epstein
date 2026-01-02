import json
import sys
from pathlib import Path
# ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ocr_watch import run_once


def test_ocr_watch_emits_summary_and_alerts(tmp_path, caplog):
    p = tmp_path / 'processing_status.jsonl'
    entries = [
        {'sha256': 'a', 'ocr_status': 'ok', 'before_chars': 10, 'after_chars': 500},
        {'sha256': 'b', 'ocr_status': 'ocr_failed', 'before_chars': 0, 'after_chars': 0},
        {'sha256': 'c', 'ocr_status': 'ocr_empty', 'before_chars': 0, 'after_chars': 0, 'fallback_status': 'fallback_empty'}
    ]
    with p.open('w') as fh:
        for e in entries:
            fh.write(json.dumps(e) + '\n')
    out = tmp_path / 'ocr_summary.json'

    summary, alerts = run_once(status_path=p, out_path=out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data['total'] == 3
    # because at least one failed and one empty, expect at least one alert
    assert isinstance(alerts, list)
    assert len(alerts) >= 1
