import json
from pathlib import Path

from scripts import ocr_summary


def test_ocr_summary(tmp_path):
    p = tmp_path / 'processing_status.jsonl'
    entries = [
        {'sha256': 'a', 'ocr_status': 'ok', 'before_chars': 10, 'after_chars': 100},
        {'sha256': 'b', 'ocr_status': 'ocr_failed', 'before_chars': 0, 'after_chars': 0},
    ]
    with p.open('w') as fh:
        for e in entries:
            fh.write(json.dumps(e) + '\n')
    # monkeypatch the status path in module
    out = tmp_path / 'ocr_summary.json'
    # temporarily override constants
    import importlib
    import scripts.ocr_summary as mod
    mod.STATUS_FILE = p
    mod.OUT_FILE = out
    mod.main()
    data = json.loads(out.read_text())
    assert data['total'] == 2
    assert data['counts']['ok'] == 1
    assert data['counts']['ocr_failed'] == 1
