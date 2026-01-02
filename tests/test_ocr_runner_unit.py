import io
import json
import os
import sys
import shutil
import subprocess
from pathlib import Path

import pytest

# ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import ocr_runner


class DummyProc:
    def __init__(self, stdout=b'', returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_pdftotext_count(monkeypatch, tmp_path):
    # monkeypatch subprocess.run to return a dummy stdout
    def fake_run(*args, **kwargs):
        return DummyProc(stdout=b'hello world')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    p = tmp_path / 'f.pdf'
    p.write_bytes(b'%PDF-1.4')
    cnt = ocr_runner.pdftotext_count(str(p))
    assert cnt == len(b'hello world')


def test_run_ocrmypdf_success(monkeypatch, tmp_path):
    def fake_run(args, stdout=None, stderr=None, timeout=None):
        return DummyProc(returncode=0)

    monkeypatch.setattr(subprocess, 'run', fake_run)
    input_pdf = tmp_path / 'in.pdf'
    out_pdf = tmp_path / 'out.pdf'
    log = tmp_path / 'log.txt'
    input_pdf.write_bytes(b'%PDF-1.4')
    rc = ocr_runner.run_ocrmypdf(str(input_pdf), str(out_pdf), str(log), timeout=1)
    assert rc == 0


def test_fallback_tesseract(monkeypatch, tmp_path):
    # emulate pdftoppm creating PNG files and tesseract returning text
    created = []

    def fake_pdftoppm(args, stdout=None, stderr=None, timeout=None):
        # create two dummy png files
        base = args[-1]
        p1 = Path(f'/tmp/{Path(base).name}_page-1.png')
        p2 = Path(f'/tmp/{Path(base).name}_page-2.png')
        p1.write_bytes(b'PNG')
        p2.write_bytes(b'PNG')
        created.extend([p1, p2])
        return DummyProc(returncode=0)

    def fake_tesseract(args, stdout=None, stderr=None, check=False, timeout=None):
        return DummyProc(stdout=b'text on page')

    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: fake_pdftoppm(*a, **k) if 'pdftoppm' in a[0] else fake_tesseract(*a, **k))

    out_txt = tmp_path / 'out.txt'
    chars = ocr_runner.fallback_tesseract(str(tmp_path / 'dummy.pdf'), out_txt)
    assert out_txt.exists()
    assert chars > 0
    # cleanup
    for f in created:
        try:
            f.unlink()
        except Exception:
            pass
