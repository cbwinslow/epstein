#!/usr/bin/env python3
"""epstein_bulk_downloader.py

Date: 2025-12-29
Author: ChatGPT (for Blaine Winslow / cbwinslow)

Summary
-------
Unified, resumable, verifiable bulk downloader framework for multiple public Epstein-related
releases, with a pluggable "source" architecture.

Supported sources (today)
-------------------------
1) DOJ Epstein Library → DOJ Disclosures (Data Set N ZIPs + extract)
   - Auto-discovers dataset "files" pages and ZIP links from the DOJ disclosures index.

2) FBI Vault → Jeffrey Epstein FOIA PDFs (Parts 01..N)
   - Auto-discovers Part links from the FBI Vault listing page.
   - Downloads PDFs via the stable "/at_download/file" endpoint.

3) U.S. House Oversight press releases (Drive + Dropbox public links)
   - Auto-discovers drive.google.com and dropbox.com links from Oversight release pages.
   - Uses external tools for bulk folder download:
       * Google Drive: gdown --folder <URL> (recommended)
       * Dropbox: rclone recommended (folder shares are not reliably downloadable via raw HTTP)

Outputs
-------
Base: <out_dir>
- raw/doj_disclosures/zips/*.zip
- raw/doj_disclosures/extracted/dataset_XX/*
- raw/fbi_vault/*.pdf
- raw/house_oversight/<release_slug>/*
- manifests/<source>.manifest.jsonl
- Logs: <log_dir>/CBW-epstein_bulk_downloader.log

Security Notes
--------------
- No downloaded content is executed.
- ZIP Slip protections are applied for ZIP extraction.
- Writes are confined to output directory.

Modification Log
----------------
- 2025-12-29: Added FBI Vault + House Oversight source framework.
- 2025-12-28: Initial DOJ Disclosures downloader.

"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import time
import urllib.parse
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# -----------------------------
# Constants / Defaults
# -----------------------------
DEFAULT_DOJ_INDEX_URL = "https://www.justice.gov/epstein/doj-disclosures"
DEFAULT_FBI_VAULT_EPSTEIN_URL = "https://vault.fbi.gov/jeffrey-epstein"
DEFAULT_USER_AGENT = "cbw-epstein-downloader/1.1 (+https://cloudcurio.cc)"
DEFAULT_TIMEOUT_S = 60
DEFAULT_MAX_RETRIES = 8
DEFAULT_BACKOFF_BASE_S = 1.75
DEFAULT_MAX_WORKERS = 3
DEFAULT_CHUNK_BYTES = 8 * 1024 * 1024

DEFAULT_RAW_DIR = "raw"
DEFAULT_MANIFEST_DIR = "manifests"
DEFAULT_LOG_DIR = "/tmp"

HOUSE_OVERSIGHT_RELEASES = [
    "https://oversight.house.gov/release/oversight-committee-releases-epstein-records-provided-by-the-department-of-justice/",
    "https://oversight.house.gov/release/oversight-committee-releases-additional-epstein-estate-documents/",
]


# -----------------------------
# Logging
# -----------------------------

class Log:
    def __init__(self, logfile: Path, verbose: bool = False):
        self.logfile = logfile
        self.verbose = verbose
        self.logfile.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, level: str, msg: str):
        ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line)
        with self.logfile.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def info(self, msg: str):
        self._write("INFO", msg)

    def warn(self, msg: str):
        self._write("WARN", msg)

    def error(self, msg: str):
        self._write("ERROR", msg)

    def debug(self, msg: str):
        if self.verbose:
            self._write("DEBUG", msg)


# -----------------------------
# Data Models
# -----------------------------

@dataclasses.dataclass(frozen=True)
class DownloadTask:
    source: str
    name: str
    url: str
    dest: Path
    kind: str  # zip | pdf | folder
    meta: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class DownloadResult:
    source: str
    name: str
    url: str
    dest: Path
    kind: str
    ok: bool
    bytes_downloaded: int = 0
    sha256: str = ""
    extracted_files: int = 0
    error: Optional[str] = None
    meta: dict = dataclasses.field(default_factory=dict)


# -----------------------------
# Helpers
# -----------------------------

def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def safe_int(s: str, default: int = 0) -> int:
    try:
        return int(s)
    except Exception:
        return default


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def requests_session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent})
    return s


def normalize_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href)


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


# -----------------------------
# HTTP
# -----------------------------

def http_get_text(sess: requests.Session, url: str, timeout_s: int, max_retries: int, backoff_base_s: float, log: Log) -> str:
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            log.debug(f"GET {url} (attempt {attempt}/{max_retries})")
            r = sess.get(url, timeout=timeout_s)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            sleep_s = backoff_base_s ** min(attempt, 6)
            log.warn(f"GET failed ({attempt}/{max_retries}) for {url}: {e} | backoff {sleep_s:.1f}s")
            time.sleep(sleep_s)
    raise RuntimeError(f"Failed to GET {url} after {max_retries} attempts: {last_err}")


def head_content_length(sess: requests.Session, url: str, timeout_s: int, log: Log) -> Optional[int]:
    try:
        r = sess.head(url, timeout=timeout_s, allow_redirects=True)
        if r.status_code >= 400:
            return None
        cl = r.headers.get("Content-Length")
        if cl is None:
            return None
        return int(cl)
    except Exception as e:
        log.debug(f"HEAD failed for {url}: {e}")
        return None


# -----------------------------
# Downloading (resume + retries)
# -----------------------------

def download_with_resume(
    sess: requests.Session,
    url: str,
    dest: Path,
    timeout_s: int,
    max_retries: int,
    backoff_base_s: float,
    chunk_bytes: int,
    dry_run: bool,
    log: Log,
) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        log.info(f"[dry-run] Would download: {url} -> {dest}")
        return 0

    remote_len = head_content_length(sess, url, timeout_s, log)

    for attempt in range(1, max_retries + 1):
        try:
            existing = dest.stat().st_size if dest.exists() else 0
            headers: Dict[str, str] = {}
            mode = "ab" if existing > 0 else "wb"

            if remote_len is not None and existing == remote_len:
                log.info(f"Already downloaded (size matches): {dest.name} ({existing} bytes)")
                return existing

            if existing > 0:
                headers["Range"] = f"bytes={existing}-"
                log.info(f"Resuming {dest.name} at byte {existing}")
            else:
                log.info(f"Downloading {dest.name}")

            with sess.get(url, headers=headers, stream=True, timeout=timeout_s, allow_redirects=True) as r:
                if existing > 0 and r.status_code == 200:
                    log.warn(f"Server ignored Range; restarting download for {dest.name}")
                    mode = "wb"
                    existing = 0

                r.raise_for_status()

                bytes_written = existing
                with dest.open(mode, buffering=0) as f:
                    for chunk in r.iter_content(chunk_size=chunk_bytes):
                        if not chunk:
                            continue
                        f.write(chunk)
                        bytes_written += len(chunk)

            final_size = dest.stat().st_size
            if remote_len is not None and final_size != remote_len:
                raise RuntimeError(f"Size mismatch for {dest.name}: got {final_size}, expected {remote_len}")

            return final_size

        except Exception as e:
            sleep_s = backoff_base_s ** min(attempt, 6)
            log.warn(f"Download failed ({attempt}/{max_retries}) for {url}: {e} | backoff {sleep_s:.1f}s")
            time.sleep(sleep_s)

    raise RuntimeError(f"Failed to download {url} after {max_retries} attempts")


# -----------------------------
# ZIP validation + extraction
# -----------------------------

def validate_zip(path: Path) -> Tuple[bool, Optional[str]]:
    try:
        with zipfile.ZipFile(path, "r") as z:
            bad = z.testzip()
            if bad is not None:
                return False, f"Corrupt zip member: {bad}"
        return True, None
    except Exception as e:
        return False, str(e)


def extract_zip(zip_path: Path, out_dir: Path, dry_run: bool, log: Log) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        log.info(f"[dry-run] Would extract: {zip_path} -> {out_dir}")
        return 0

    tmp_dir = out_dir.parent / f".{out_dir.name}.extracting"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    extracted_files = 0
    with zipfile.ZipFile(zip_path, "r") as z:
        for m in z.infolist():
            target_path = (tmp_dir / m.filename).resolve()
            if not str(target_path).startswith(str(tmp_dir.resolve())):
                raise RuntimeError(f"Blocked potential Zip Slip path: {m.filename}")
            z.extract(m, path=tmp_dir)
            extracted_files += 1

    for src in tmp_dir.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(tmp_dir)
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            continue
        shutil.move(str(src), str(dst))

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return extracted_files


# -----------------------------
# Manifest
# -----------------------------

def append_manifest(manifest_path: Path, record: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# -----------------------------
# Source: DOJ Disclosures
# -----------------------------

def discover_doj_tasks(sess: requests.Session, index_url: str, out_dir: Path, timeout_s: int, max_retries: int, backoff_base_s: float, log: Log) -> List[DownloadTask]:
    html = http_get_text(sess, index_url, timeout_s, max_retries, backoff_base_s, log)

    dataset_page_matches = re.findall('href="([^"]*data-set-[0-9]+-files)"', html, flags=re.IGNORECASE)
    dataset_pages = sorted({normalize_url(index_url, m) for m in dataset_page_matches})

    if not dataset_pages:
        log.warn("DOJ: Could not find explicit dataset file pages on index; attempting broader extraction.")
        dataset_page_matches = re.findall('href="([^"]*data-set-[0-9]+[^\"]*)"', html, flags=re.IGNORECASE)
        dataset_pages = sorted({normalize_url(index_url, m) for m in dataset_page_matches if "data-set" in m})

    tasks: List[DownloadTask] = []
    raw_base = out_dir / DEFAULT_RAW_DIR / "doj_disclosures"
    zips_dir = raw_base / "zips"
    extracted_dir = raw_base / "extracted"

    for page_url in dataset_pages:
        m = re.search("data-set-([0-9]+)", page_url)
        if not m:
            continue
        ds_num = safe_int(m.group(1), default=-1)
        if ds_num <= 0:
            continue

        page_html = http_get_text(sess, page_url, timeout_s, max_retries, backoff_base_s, log)
        zip_links = re.findall('href="([^"]+\.zip)"', page_html, flags=re.IGNORECASE)
        if not zip_links:
            log.warn(f"DOJ: No ZIP link found on dataset page {page_url} (Data Set {ds_num}).")
            continue

        zip_url = normalize_url(page_url, zip_links[0])
        zip_path = zips_dir / f"doj_dataset_{ds_num:02d}.zip"
        ds_extract_dir = extracted_dir / f"dataset_{ds_num:02d}"

        tasks.append(
            DownloadTask(
                source="doj_disclosures",
                name=f"DOJ Data Set {ds_num:02d} ZIP",
                url=zip_url,
                dest=zip_path,
                kind="zip",
                meta={"dataset_num": ds_num, "dataset_page_url": page_url, "extract_dir": str(ds_extract_dir)},
            )
        )

    seen: set = set()
    uniq: List[DownloadTask] = []
    for t in sorted(tasks, key=lambda x: x.meta.get("dataset_num", 9999)):
        dn = t.meta.get("dataset_num")
        if dn in seen:
            continue
        seen.add(dn)
        uniq.append(t)

    log.info(f"DOJ: Discovered {len(uniq)} dataset ZIP task(s).")
    return uniq


# -----------------------------
# Source: FBI Vault
# -----------------------------

def discover_fbi_vault_tasks(sess: requests.Session, vault_url: str, out_dir: Path, timeout_s: int, max_retries: int, backoff_base_s: float, log: Log) -> List[DownloadTask]:
    html = http_get_text(sess, vault_url, timeout_s, max_retries, backoff_base_s, log)

    part_links = re.findall('href="([^"]*/Jeffrey%20Epstein%20Part%20[0-9]{2})"', html, flags=re.IGNORECASE)
    part_links += re.findall('href="([^"]*/jeffrey-epstein/Jeffrey%20Epstein%20Part%20[0-9]{2})"', html, flags=re.IGNORECASE)
    parts = sorted({normalize_url(vault_url, p) for p in part_links})

    raw_base = out_dir / DEFAULT_RAW_DIR / "fbi_vault"
    raw_base.mkdir(parents=True, exist_ok=True)

    tasks: List[DownloadTask] = []
    for part_url in parts:
        m = re.search("Part%20([0-9]{2})", part_url)
        if not m:
            continue
        part_num = safe_int(m.group(1), default=-1)
        if part_num < 0:
            continue

        dl_url = part_url.rstrip("/") + "/at_download/file"
        dest = raw_base / f"fbi_epstein_part_{part_num:02d}.pdf"

        tasks.append(
            DownloadTask(
                source="fbi_vault",
                name=f"FBI Vault Jeffrey Epstein Part {part_num:02d}",
                url=dl_url,
                dest=dest,
                kind="pdf",
                meta={"part_num": part_num, "part_page_url": part_url},
            )
        )

    seen = set()
    uniq: List[DownloadTask] = []
    for t in sorted(tasks, key=lambda x: x.meta.get("part_num", 9999)):
        pn = t.meta.get("part_num")
        if pn in seen:
            continue
        seen.add(pn)
        uniq.append(t)

    log.info(f"FBI: Discovered {len(uniq)} part PDF task(s).")
    return uniq


# -----------------------------
# Source: House Oversight (Drive + Dropbox)
# -----------------------------

def extract_house_folder_links(page_html: str, page_url: str) -> List[str]:
    links = re.findall('href="([^"]+)"', page_html, flags=re.IGNORECASE)
    abs_links = [normalize_url(page_url, href) for href in links]
    return [u for u in abs_links if ("drive.google.com" in u or "dropbox.com" in u)]


def discover_house_oversight_tasks(sess: requests.Session, release_urls: List[str], out_dir: Path, timeout_s: int, max_retries: int, backoff_base_s: float, log: Log) -> List[DownloadTask]:
    tasks: List[DownloadTask] = []
    raw_base = out_dir / DEFAULT_RAW_DIR / "house_oversight"

    for rel_url in release_urls:
        html = http_get_text(sess, rel_url, timeout_s, max_retries, backoff_base_s, log)
        folder_links = extract_house_folder_links(html, rel_url)

        slug = urllib.parse.urlparse(rel_url).path.strip("/").split("/")[-1]
        dest_dir = raw_base / slug

        for u in folder_links:
            if "drive.google.com" in u:
                tasks.append(
                    DownloadTask(
                        source="house_oversight",
                        name=f"House Oversight (Drive) {slug}",
                        url=u,
                        dest=dest_dir,
                        kind="folder",
                        meta={"release_url": rel_url, "slug": slug, "provider": "gdrive"},
                    )
                )
            elif "dropbox.com" in u:
                tasks.append(
                    DownloadTask(
                        source="house_oversight",
                        name=f"House Oversight (Dropbox) {slug}",
                        url=u,
                        dest=dest_dir,
                        kind="folder",
                        meta={"release_url": rel_url, "slug": slug, "provider": "dropbox"},
                    )
                )

    uniq: Dict[Tuple[str, str], DownloadTask] = {}
    for t in tasks:
        key = (t.meta.get("provider", ""), t.meta.get("slug", ""))
        uniq.setdefault(key, t)

    out = [uniq[k] for k in sorted(uniq)]
    log.info(f"HOUSE: Discovered {len(out)} folder task(s) across {len(release_urls)} release page(s).")
    return out


def run_gdown_folder(url: str, dest_dir: Path, dry_run: bool, log: Log) -> None:
    if which("gdown") is None:
        raise RuntimeError("gdown not found. Install with: python3 -m pip install --user gdown")

    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["gdown", "--folder", url, "--output", str(dest_dir)]

    if dry_run:
        log.info(f"[dry-run] Would run: {' '.join(cmd)}")
        return

    log.info(f"Running gdown folder download into {dest_dir} ...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gdown failed: {proc.stderr.strip() or proc.stdout.strip()}")


def run_dropbox_hint(url: str) -> None:
    raise RuntimeError(
        "Dropbox folder shares are best downloaded via rclone (recommended) or Dropbox API. "
        f"Detected Dropbox link: {url}"
    )


# -----------------------------
# Task execution
# -----------------------------

def execute_task(task: DownloadTask, sess: requests.Session, out_dir: Path, timeout_s: int, max_retries: int, backoff_base_s: float, chunk_bytes: int, dry_run: bool, log: Log) -> DownloadResult:
    manifest_path = out_dir / DEFAULT_MANIFEST_DIR / f"{task.source}.manifest.jsonl"

    try:
        if task.kind in ("zip", "pdf"):
            bytes_dl = download_with_resume(
                sess,
                task.url,
                task.dest,
                timeout_s=timeout_s,
                max_retries=max_retries,
                backoff_base_s=backoff_base_s,
                chunk_bytes=chunk_bytes,
                dry_run=dry_run,
                log=log,
            )

            sha = ""
            if not dry_run:
                sha = sha256_file(task.dest)

            extracted_files = 0
            if task.kind == "zip":
                if not dry_run:
                    ok, err = validate_zip(task.dest)
                    if not ok:
                        raise RuntimeError(f"ZIP validation failed: {err}")
                extract_dir = Path(task.meta.get("extract_dir", ""))
                extracted_files = extract_zip(task.dest, extract_dir, dry_run=dry_run, log=log)

            rec = {
                "ts_utc": now_iso(),
                "source": task.source,
                "name": task.name,
                "url": task.url,
                "dest": str(task.dest),
                "kind": task.kind,
                "bytes": (task.dest.stat().st_size if task.dest.exists() and not dry_run else 0),
                "sha256": sha,
                "extracted_files": extracted_files,
                "ok": True,
                "meta": task.meta,
            }
            if not dry_run:
                append_manifest(manifest_path, rec)

            return DownloadResult(
                source=task.source,
                name=task.name,
                url=task.url,
                dest=task.dest,
                kind=task.kind,
                ok=True,
                bytes_downloaded=bytes_dl,
                sha256=sha,
                extracted_files=extracted_files,
                meta=task.meta,
            )

        if task.kind == "folder":
            provider = task.meta.get("provider")
            if provider == "gdrive":
                run_gdown_folder(task.url, task.dest, dry_run=dry_run, log=log)
            elif provider == "dropbox":
                run_dropbox_hint(task.url)
            else:
                raise RuntimeError(f"Unknown folder provider: {provider}")

            rec = {
                "ts_utc": now_iso(),
                "source": task.source,
                "name": task.name,
                "url": task.url,
                "dest": str(task.dest),
                "kind": task.kind,
                "ok": True,
                "meta": task.meta,
            }
            if not dry_run:
                append_manifest(manifest_path, rec)

            return DownloadResult(source=task.source, name=task.name, url=task.url, dest=task.dest, kind=task.kind, ok=True, meta=task.meta)

        raise RuntimeError(f"Unsupported task kind: {task.kind}")

    except Exception as e:
        rec = {
            "ts_utc": now_iso(),
            "source": task.source,
            "name": task.name,
            "url": task.url,
            "dest": str(task.dest),
            "kind": task.kind,
            "ok": False,
            "error": str(e),
            "meta": task.meta,
        }
        if not dry_run:
            append_manifest(manifest_path, rec)

        return DownloadResult(source=task.source, name=task.name, url=task.url, dest=task.dest, kind=task.kind, ok=False, error=str(e), meta=task.meta)


# -----------------------------
# Main
# -----------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Unified Epstein files downloader (DOJ + FBI + House Oversight links).")
    p.add_argument("--out-dir", default=str(Path.cwd() / "epstein_project"), help="Base output directory")
    p.add_argument("--sources", default="doj,fbi,house", help="Comma-separated sources: doj,fbi,house")

    p.add_argument("--doj-index-url", default=DEFAULT_DOJ_INDEX_URL, help="DOJ disclosures index URL")
    p.add_argument("--fbi-vault-url", default=DEFAULT_FBI_VAULT_EPSTEIN_URL, help="FBI Vault Epstein URL")
    p.add_argument("--house-release-url", action="append", default=[], help="House Oversight press release URL (repeatable)")

    p.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS, help="Parallel worker threads")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S, help="HTTP timeout seconds")
    p.add_argument("--retries", type=int, default=DEFAULT_MAX_RETRIES, help="Max retries")
    p.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF_BASE_S, help="Backoff base")
    p.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK_BYTES, help="Download chunk size")
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent header")
    p.add_argument("--dry-run", action="store_true", help="Show plan; do not download")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    p.add_argument("--log-dir", default=DEFAULT_LOG_DIR, help="Log directory (default: /tmp)")

    args = p.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    logfile = Path(args.log_dir).expanduser().resolve() / "CBW-epstein_bulk_downloader.log"
    log = Log(logfile=logfile, verbose=args.verbose)

    log.info("Starting epstein_bulk_downloader (unified)...")
    log.info(f"Output dir: {out_dir}")
    log.info(f"Sources: {args.sources}")
    log.info(f"Dry-run: {args.dry_run}")

    sess = requests_session(args.user_agent)

    sources = {s.strip().lower() for s in args.sources.split(",") if s.strip()}

    tasks: List[DownloadTask] = []

    if "doj" in sources:
        tasks.extend(discover_doj_tasks(sess, args.doj_index_url, out_dir, args.timeout, args.retries, args.backoff, log))

    if "fbi" in sources:
        tasks.extend(discover_fbi_vault_tasks(sess, args.fbi_vault_url, out_dir, args.timeout, args.retries, args.backoff, log))

    if "house" in sources:
        rels = args.house_release_url[:] if args.house_release_url else HOUSE_OVERSIGHT_RELEASES
        tasks.extend(discover_house_oversight_tasks(sess, rels, out_dir, args.timeout, args.retries, args.backoff, log))

    if not tasks:
        log.error("No tasks discovered. Exiting.")
        return 2

    log.info(f"Planned tasks: {len(tasks)}")
    for t in tasks:
        log.info(f"Plan: [{t.source}] {t.name} -> {t.dest}")

    if args.dry_run:
        log.info("Dry-run complete.")
        return 0

    file_tasks = [t for t in tasks if t.kind in ("zip", "pdf")]
    folder_tasks = [t for t in tasks if t.kind == "folder"]

    results: List[DownloadResult] = []

    if file_tasks:
        log.info(f"Executing {len(file_tasks)} file task(s) with max_workers={max(1, args.max_workers)}")
        with cf.ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as ex:
            futs = [
                ex.submit(execute_task, t, sess, out_dir, args.timeout, args.retries, args.backoff, args.chunk_bytes, args.dry_run, log)
                for t in file_tasks
            ]
            for fut in cf.as_completed(futs):
                res = fut.result()
                results.append(res)
                if res.ok:
                    log.info(f"OK [{res.source}] {res.name}")
                else:
                    log.error(f"FAIL [{res.source}] {res.name}: {res.error}")

    for t in folder_tasks:
        log.info(f"Executing folder task: [{t.source}] {t.name}")
        res = execute_task(t, sess, out_dir, args.timeout, args.retries, args.backoff, args.chunk_bytes, args.dry_run, log)
        results.append(res)
        if res.ok:
            log.info(f"OK [{res.source}] {res.name}")
        else:
            log.error(f"FAIL [{res.source}] {res.name}: {res.error}")

    ok = [r for r in results if r.ok]
    bad = [r for r in results if not r.ok]

    log.info("Summary:")
    log.info(f"  Successful: {len(ok)}")
    log.info(f"  Failed:     {len(bad)}")
    log.info(f"Logs: {logfile}")
    log.info(f"Manifests dir: {out_dir / DEFAULT_MANIFEST_DIR}")

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
