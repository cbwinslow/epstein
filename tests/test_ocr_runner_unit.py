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
    rc = ocr_runner.run_ocrmypdf(str(input_pdf), str(out_pdf), str(log), timeout=1, skip_text=False, rotate_pages=False, optimize_level=None)
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


def test_fallback_psm_selection(monkeypatch, tmp_path):
    # simulate pdftoppm creating PNG pages
    pages = [tmp_path / 'p1.png', tmp_path / 'p2.png']
    for p in pages:
        p.write_bytes(b'PNG')

    # simulate tesseract: return different outputs depending on '--psm' arg
    def fake_run(args, stdout=None, stderr=None, check=False, timeout=None):
        cmd = args
        if 'pdftoppm' in cmd[0]:
            return DummyProc(returncode=0)
        # args contains '--psm' and the mode
        try:
            mode = cmd[cmd.index('--psm')+1]
        except Exception:
            mode = '3'
        if mode == '3':
            return DummyProc(stdout=b'a')
        if mode == '6':
            return DummyProc(stdout=b'aaaaa')
        if mode == '11':
            return DummyProc(stdout=b'aa')
        return DummyProc(stdout=b'')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    out_txt = tmp_path / 'out_psm.txt'
    # create dummy pages in /tmp as our function will search there; copy our created pages to /tmp
    tmp1 = Path('/tmp') / (out_txt.stem + '_page-1.png')
    tmp2 = Path('/tmp') / (out_txt.stem + '_page-2.png')
    tmp1.write_bytes(b'PNG')
    tmp2.write_bytes(b'PNG')
    try:
        chars = ocr_runner.fallback_tesseract(str(tmp_path / 'dummy.pdf'), out_txt)
        assert out_txt.exists()
        txt = out_txt.read_text(encoding='utf-8')
        # best per page should pick mode 6 (5 chars) then mode 6 again -> total 10
        assert chars == len(txt)
        assert chars >= 10
    finally:
        try:
            tmp1.unlink()
            tmp2.unlink()
        except Exception:
            pass
