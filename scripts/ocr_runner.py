#!/usr/bin/env python3
"""OCR runner for the Epstein project.

Primary: ocrmypdf
Fallback: pdftoppm -> tesseract
Writes per-file JSON lines to `epstein_project/processing_status.jsonl` (append-only).
"""
import argparse
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

# Allow overriding root for tests via EPSTEIN_ROOT_OVERRIDE
ROOT = Path(os.environ.get('EPSTEIN_ROOT_OVERRIDE') or Path(__file__).resolve().parents[1])
MANIFEST = ROOT / 'epstein_project' / 'manifest.jsonl'
TEXT_DIR = ROOT / 'epstein_project' / 'text'
OCR_DIR = ROOT / 'epstein_project' / 'ocr'
OCR_FALLBACK_DIR = ROOT / 'epstein_project' / 'ocr_fallback'
STATUS_FILE = ROOT / 'epstein_project' / 'processing_status.jsonl'
LOG_DIR = ROOT / 'epstein_project' / 'logs' / 'ocr'

for p in (OCR_DIR, OCR_FALLBACK_DIR, LOG_DIR):
    p.mkdir(parents=True, exist_ok=True)

# prefer user-local jbig2
os.environ['PATH'] = str(Path.home() / '.local' / 'bin') + ':' + os.environ.get('PATH', '')

DEFAULTS = {
    'min_pdf_bytes': 300_000,
    'max_text_bytes': 500,
    'batch': 50,
    'ocr_timeout': 300,
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def load_manifest():
    m = {}
    if not MANIFEST.exists():
        return m
    with MANIFEST.open('r') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if 'sha256' in obj:
                    m[obj['sha256']] = obj
            except Exception:
                continue
    return m


def pdftotext_count(path):
    try:
        p = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', str(path), '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=60)
        return len(p.stdout or b'')
    except Exception:
        return 0


def jbig2_available():
    exe = shutil.which('jbig2') or shutil.which('jbig2enc')
    if not exe:
        return False
    return os.access(exe, os.X_OK)


def run_ocrmypdf(input_pdf, out_pdf, log_path, timeout, *, skip_text, rotate_pages, optimize_level):
    if optimize_level is None and not jbig2_available():
        optimize_level = 0
    with open(log_path, 'wb') as lf:
        # avoid conflicting flags: do not use --force together with --skip-text
        cmd = ['ocrmypdf', '--deskew', '--output-type', 'pdf']
        if not skip_text:
            cmd.append('--force')
        if skip_text:
            cmd.append('--skip-text')
        if rotate_pages:
            cmd.append('--rotate-pages')
        if optimize_level is not None:
            cmd.extend(['--optimize', str(optimize_level)])
        cmd.extend([str(input_pdf), str(out_pdf)])
        proc = subprocess.run(cmd, stdout=lf, stderr=lf, timeout=timeout)
    return proc.returncode


def fallback_tesseract(input_pdf, out_txt_path):
    # use pdftoppm -> tesseract
    tmp_prefix = f'/tmp/{out_txt_path.stem}_page'
    try:
        subprocess.run(['pdftoppm', '-r', '300', str(input_pdf), tmp_prefix], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        pages = sorted(Path('/tmp').glob(f"{out_txt_path.stem}_page*.png"))
        parts = []
        for pg in pages:
            p = subprocess.run(['tesseract', str(pg), 'stdout', '-l', 'eng'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=60)
            parts.append(p.stdout.decode('utf-8', errors='ignore'))
        txt = '\n'.join(parts)
        out_txt_path.write_text(txt, encoding='utf-8')
        # if fallback produced nothing, preserve first page image for debugging
        if len(txt.strip()) == 0 and pages:
            debug_dir = LOG_DIR / 'ocr_debug_pages'
            debug_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(pages[0], debug_dir / f"{out_txt_path.stem}_page-1.png")
            except Exception:
                pass
        return len(txt)
    finally:
        for pg in Path('/tmp').glob(f"{out_txt_path.stem}_page*.png"):
            try:
                pg.unlink()
            except Exception:
                pass


def atomic_append_status(rec):
    tmp = STATUS_FILE.with_suffix('.tmp')
    with tmp.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    # move append into live file (simple approach - append tmp to file and remove tmp)
    with tmp.open('r', encoding='utf-8') as rf, STATUS_FILE.open('a', encoding='utf-8') as wf:
        wf.write(rf.read())
    tmp.unlink()


def main(batch, min_pdf_bytes, max_text_bytes, ocr_timeout, skip_text, rotate_pages, optimize_level):
    manifest = load_manifest()
    candidates = []
    for txt in TEXT_DIR.glob('*.txt'):
        try:
            size = txt.stat().st_size
        except Exception:
            continue
        if size <= max_text_bytes:
            sha = txt.stem
            entry = manifest.get(sha)
            if not entry:
                continue
            pdf_bytes = entry.get('bytes', 0)
            if pdf_bytes and pdf_bytes >= min_pdf_bytes:
                candidates.append(sha)
        if len(candidates) >= batch:
            break

    logging.info('Selected %d candidates', len(candidates))

    for sha in candidates:
        rec = {'sha256': sha, 'ts_start': int(time.time())}
        entry = manifest.get(sha, {})
        path = entry.get('path') or entry.get('url')
        rec['input_pdf'] = path
        rec['before_chars'] = 0
        rec['after_chars'] = 0
        rec['ocr_status'] = None
        rec['fallback_status'] = None
        rec['fallback_chars'] = 0
        rec['replaced_text'] = False
        logfile = LOG_DIR / f'{sha}.ocr.log'
        rec['log'] = str(logfile)

        if not path or not Path(path).is_file():
            rec['ocr_status'] = 'input_missing'
            rec['error'] = f'input missing: {path}'
            atomic_append_status(rec)
            continue

        rec['before_chars'] = pdftotext_count(path)

        out_pdf = OCR_DIR / f'{sha}.ocr.pdf'
        try:
            ret = run_ocrmypdf(
                path,
                out_pdf,
                logfile,
                ocr_timeout,
                skip_text=skip_text,
                rotate_pages=rotate_pages,
                optimize_level=optimize_level,
            )
            rec['ocr_return'] = ret
            if ret != 0:
                rec['ocr_status'] = 'ocr_failed'
            else:
                rec['after_chars'] = pdftotext_count(out_pdf)
                rec['ocr_status'] = 'ok' if rec['after_chars'] > 0 else 'ocr_empty'
        except subprocess.TimeoutExpired:
            rec['ocr_status'] = 'ocr_timeout'
        except Exception as e:
            rec['ocr_status'] = 'ocr_error'
            rec['error'] = str(e)

        # fallback if needed
        if rec['ocr_status'] != 'ok' or rec['after_chars'] < 200:
            fb_txt = OCR_FALLBACK_DIR / f'{sha}.txt'
            try:
                fb_chars = fallback_tesseract(path, fb_txt)
                rec['fallback_chars'] = fb_chars
                rec['fallback_status'] = 'ok' if fb_chars > 0 else 'fallback_empty'
                # replace original if better
                orig_txt = TEXT_DIR / f'{sha}.txt'
                orig_len = orig_txt.stat().st_size if orig_txt.exists() else 0
                if fb_chars > orig_len and fb_chars >= 200:
                    # backup
                    bk = ROOT / 'epstein_project' / 'text_pre_ocr_fix'
                    bk.mkdir(parents=True, exist_ok=True)
                    if orig_txt.exists():
                        shutil.copy2(orig_txt, bk / orig_txt.name)
                    orig_txt.write_text(fb_txt.read_text(encoding='utf-8'), encoding='utf-8')
                    rec['replaced_text'] = True
            except subprocess.TimeoutExpired:
                rec['fallback_status'] = 'fallback_timeout'
            except Exception as e:
                rec['fallback_status'] = 'fallback_error'
                rec['fallback_error'] = str(e)

        rec['ts_end'] = int(time.time())
        atomic_append_status(rec)
        logging.info('Processed %s: ocr_status=%s after=%d fallback=%s fb_chars=%d replaced=%s', sha, rec.get('ocr_status'), rec.get('after_chars'), rec.get('fallback_status'), rec.get('fallback_chars'), rec.get('replaced_text'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--batch', type=int, default=DEFAULTS['batch'])
    p.add_argument('--min-bytes', type=int, default=DEFAULTS['min_pdf_bytes'])
    p.add_argument('--max-text-bytes', type=int, default=DEFAULTS['max_text_bytes'])
    p.add_argument('--timeout', type=int, default=DEFAULTS['ocr_timeout'])
    p.add_argument('--skip-text', action='store_true', default=False, help='Skip pages that already have text (default: false)')
    p.add_argument('--no-skip-text', dest='skip_text', action='store_false')
    p.add_argument('--rotate-pages', action='store_true', default=True, help='Auto-rotate pages (default: true)')
    p.add_argument('--no-rotate-pages', dest='rotate_pages', action='store_false')
    p.add_argument('--optimize', type=int, default=None, help='Pass through to ocrmypdf --optimize (default: auto)')
    args = p.parse_args()
    main(args.batch, args.min_bytes, args.max_text_bytes, args.timeout, args.skip_text, args.rotate_pages, args.optimize)
