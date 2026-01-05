#!/usr/bin/env python3
"""OCR runner for the Epstein project.

Primary: ocrmypdf
Fallback: pdftoppm -> tesseract
Writes per-file JSON lines to `epstein_project/processing_status.jsonl` (append-only).
"""
import argparse
import hashlib
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

def is_image_file(path: Path) -> bool:
    """Checks if a file is a common image type."""
    return path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.bmp']

def convert_image_to_pdf(image_path: Path, output_pdf_path: Path) -> bool:
    """Converts an image file to a single-page PDF."""
    try:
        # Import Pillow lazily to avoid requiring it at module import time (helps tests that don't need image conversion)
        from PIL import Image
        img = Image.open(image_path)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output_pdf_path, "PDF", resolution=300.0)
        return True
    except Exception as e:
        logging.error(f"Failed to convert image {image_path} to PDF: {e}")
        return False





def run_ocrmypdf(input_pdf, out_pdf, log_path, timeout, *, skip_text, rotate_pages, optimize_level):
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
        subprocess.run(['pdftoppm', '-r', '300', '-png', str(input_pdf), tmp_prefix], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        pages = sorted(Path('/tmp').glob(f"{out_txt_path.stem}_page*.png"))
        parts = []
        # try multiple PSM modes per page to improve OCR on tricky layouts
        psm_modes = ['3', '6', '11']
        for pg in pages:
            best = ''
            for mode in psm_modes:
                try:
                    p = subprocess.run(['tesseract', str(pg), 'stdout', '-l', 'eng', '--psm', mode], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=60)
                    txt_try = p.stdout.decode('utf-8', errors='ignore')
                    if len(txt_try) > len(best):
                        best = txt_try
                except Exception:
                    continue
            parts.append(best)
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


# thread-safe append to status file (thread + process safe on Unix via fcntl)
_STATUS_LOCK = None

def _ensure_lock():
    global _STATUS_LOCK
    if _STATUS_LOCK is None:
        import threading
        _STATUS_LOCK = threading.Lock()


def atomic_append_status(rec):
    """Append a JSON record to the status file in a thread-safe and process-safe way.

    Preference order for cross-process locking:
    1. `portalocker` if installed (cross-platform)
    2. `fcntl.flock` on Unix
    3. Fallback to in-process threading lock only
    """
    _ensure_lock()
    line = json.dumps(rec, ensure_ascii=False) + '\n'
    with _STATUS_LOCK:
        # Recompute status file path at call time to respect EPSTEIN_ROOT_OVERRIDE set in child processes
        root = Path(os.environ.get('EPSTEIN_ROOT_OVERRIDE') or Path(__file__).resolve().parents[1])
        status_file = root / 'epstein_project' / 'processing_status.jsonl'

        # Ensure parent directory exists so the status file can be created by any worker
        try:
            status_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Try using portalocker for cross-platform file locking
        try:
            import portalocker
            lock_flag = getattr(portalocker, 'LockFlags', None)
            if lock_flag is not None:
                flag = lock_flag.EXCLUSIVE
            else:
                flag = getattr(portalocker, 'LOCK_EX', None)
            with status_file.open('a', encoding='utf-8') as fh:
                portalocker.lock(fh, flag)
                fh.write(line)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
                try:
                    portalocker.unlock(fh)
                except Exception:
                    pass
            return
        except Exception:
            # portalocker not available or failed — fall back to fcntl on Unix
            pass

        # Fallback to fcntl for Unix-like systems
        try:
            with status_file.open('a', encoding='utf-8') as fh:
                try:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                except Exception:
                    # fcntl may not be available (e.g., Windows)
                    pass
                fh.write(line)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
                try:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
        except Exception:
            # As a last resort, try a simple write (should be rare)
            with status_file.open('a', encoding='utf-8') as fh:
                fh.write(line)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass


def main(batch, min_pdf_bytes, max_text_bytes, ocr_timeout, skip_text, rotate_pages, optimize_level, input_manifest: str = None, run_id: str = None):
    manifest = load_manifest()
    
    # Get SHAs of documents that already have processed OCR text, or have been marked as input_missing, etc.
    processed_shas = set()
    if STATUS_FILE.exists():
        with STATUS_FILE.open('r', encoding='utf-8') as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    # For filtering, need to ensure the run_id is considered
                    if run_id is None or rec.get('run_id') == run_id:
                        processed_shas.add(rec['sha256'])
                except json.JSONDecodeError:
                    continue

    candidates = []
    
    if input_manifest:
        im = Path(input_manifest)
        if im.exists():
            with im.open('r', encoding='utf-8') as fh:
                data = None
                try:
                    data = json.load(fh)
                except Exception:
                    fh.seek(0)
                    data = [json.loads(l) for l in fh if l.strip()]
            for entry in data:
                if isinstance(entry, dict):
                    sha = entry.get('sha256')
                    path_str = entry.get('path') or entry.get('url') or entry.get('file')
                    if not sha and path_str: # Generate SHA if not present
                         sha = hashlib.sha256(path_str.encode('utf-8')).hexdigest()
                    if sha and sha not in manifest: # Add to manifest if new
                         manifest[sha] = {'path': path_str, 'bytes': Path(path_str).stat().st_size if Path(path_str).exists() else 0}
                    if sha and sha not in processed_shas:
                        candidates.append(sha)
                elif isinstance(entry, str):
                    path_str = entry
                    sha = hashlib.sha256(path_str.encode('utf-8')).hexdigest()
                    if sha not in manifest:
                         manifest[sha] = {'path': path_str, 'bytes': Path(path_str).stat().st_size if Path(path_str).exists() else 0}
                    if sha not in processed_shas:
                        candidates.append(sha)
                if len(candidates) >= batch:
                    break
        else:
            logging.warning('Input manifest not found: %s', input_manifest)
    else: # Existing logic for finding PDFs to process
        for sha, entry in manifest.items():
            if sha in processed_shas:
                continue
            
            file_path = Path(entry.get('path'))
            if not file_path.exists():
                logging.warning(f"Manifest entry for SHA {sha} has non-existent path: {file_path}")
                continue

            file_suffix = file_path.suffix.lower()
            if file_suffix == '.pdf':
                pdf_bytes = entry.get('bytes', 0)
                if pdf_bytes >= min_pdf_bytes:
                    pre_ocr_text_file = TEXT_DIR / f"{sha}.txt"
                    if not pre_ocr_text_file.exists() or pre_ocr_text_file.stat().st_size <= max_text_bytes:
                        candidates.append(sha)
            elif is_image_file(file_path):
                candidates.append(sha)
            # No else here, as unsupported types are handled later in the loop

            if len(candidates) >= batch:
                break


    logging.info('Selected %d candidates for OCR processing.', len(candidates))

    for sha in candidates:
        rec = {'sha256': sha, 'ts_start': int(time.time())}
        if run_id:
            rec['run_id'] = run_id



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
    p.add_argument('--optimize', type=int, default=0, help='Pass through to ocrmypdf --optimize (default: 0)')
    p.add_argument('--input-manifest', type=str, default=None, help='Optional JSON manifest (list of {"path": "..."}) to process specific files')
    p.add_argument('--run-id', type=str, default=None, help='Optional ID for the current OCR run, used for tracking.') # New line
    args = p.parse_args()
    main(args.batch, args.min_bytes, args.max_text_bytes, args.timeout, args.skip_text, args.rotate_pages, args.optimize, input_manifest=args.input_manifest, run_id=args.run_id)

