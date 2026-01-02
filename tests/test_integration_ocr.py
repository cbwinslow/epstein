import os
import sys
import shutil
import json
import subprocess
from pathlib import Path
import pytest
from PIL import Image, ImageDraw, ImageFont
# ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.mark.skipif(shutil.which('ocrmypdf') is None or shutil.which('tesseract') is None,
                    reason='ocrmypdf or tesseract not installed')
def test_integration_ocr_runs(tmp_path):
    # create an image-based PDF that requires OCR
    img = Image.new('RGB', (600, 200), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 10), 'Hello OCR world', fill='black')
    pdf_path = tmp_path / 'image.pdf'
    img.save(str(pdf_path), 'PDF')

    # set up minimal epstein_project layout
    repo_root = Path(__file__).resolve().parents[1]
    ep = repo_root / 'epstein_project'
    tmp_ep = tmp_path / 'epstein_project'
    shutil.copytree(ep, tmp_ep)

    # insert our pdf into manifest and place at raw path expected
    sha = 'integtestsha'
    dest_raw = tmp_ep / 'raw' / 'integ_test'
    dest_raw.mkdir(parents=True, exist_ok=True)
    in_pdf = dest_raw / 'image.pdf'
    shutil.copy2(pdf_path, in_pdf)

    manifest_entry = {'sha256': sha, 'path': str(in_pdf), 'bytes': in_pdf.stat().st_size}
    manifest_file = tmp_ep / 'manifest.jsonl'
    with manifest_file.open('a') as fh:
        fh.write(json.dumps(manifest_entry) + '\n')

    # link environment variables so scripts pick up this epstein_project
    env = os.environ.copy()
    env['EPSTEIN_ROOT_OVERRIDE'] = str(tmp_ep)

    # run the ocr runner with batch=1 but override paths by editing the script to point to tmp_ep
    runner = Path(__file__).resolve().parents[1] / 'scripts' / 'ocr_runner.py'
    # run with python
    proc = subprocess.run(['python3', str(runner), '--batch', '1', '--min-bytes', '1', '--max-text-bytes', '100000'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    assert proc.returncode == 0
    # check that processing_status exists inside tmp_ep
    status_file = tmp_ep / 'processing_status.jsonl'
    assert status_file.exists()
    lines = [json.loads(l) for l in status_file.read_text().splitlines()]
    assert any(l.get('sha256') == sha for l in lines)
