#!/usr/bin/env python3
# ============================================================================
# Script Name: epstein_files_pipeline.py
# Date: 2025-12-19
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   End-to-end pipeline to analyze publicly released PDF document sets.
#
#   ✅ Core stages
#     1) Discover document URLs from trusted "seed" pages (allowlist)
#     2) Download PDFs safely (idempotent) and write a manifest with sha256
#     3) OCR PDFs into searchable PDFs (OCRmyPDF) and extract text
#     4) Redact basic identifiers (defense-in-depth) BEFORE analysis
#     5) Chunk text with overlap (with offsets) and persist chunks.jsonl
#     6) Run Named Entity Recognition (NER) and emit structured JSONL outputs
#     7) Write run tracking (runs.jsonl + failures.jsonl)
#     8) Produce "safe exports" (aggregate summaries suitable for publishing)
#
#   ✅ Critical project guarantees
#     - Provenance: every output can be traced back to doc_id (sha256) + source_url
#     - Run tracking: each run gets a run_id + metrics + failures
#     - Publication safety: redaction + safe_exports help avoid leaking identifiers
#
# Safety / Ethics Notes (IMPORTANT):
#   - Intended for research on PUBLICLY RELEASED MATERIALS.
#   - Do not use outputs to accuse individuals of crimes.
#     Treat names as "mentioned" unless a document explicitly alleges/charges.
#   - Avoid re-publishing victim-identifying info or personal identifiers.
#
# Inputs:
#   - A config JSON file specifying:
#       * seed_urls: pages to crawl for PDF links
#       * output_dir: where to store downloads and derived artifacts
#       * allow_domains: strict domain allowlist
#
# Outputs (under output_dir):
#   - downloads/            original PDFs
#   - ocr/                  OCR-processed PDFs
#   - text/                 extracted text per doc_id
#   - chunks/               chunk JSONL per doc_id (offsets + preview)
#   - entities/             entity JSONL per doc_id
#   - safe_exports/         aggregate summaries safe-ish for publishing
#   - manifest.jsonl        one line per file (doc_id sha256 + source_url)
#   - runs.jsonl            one line per pipeline run
#   - failures.jsonl        one line per doc failure
#   - run.log               runtime log
#
# Dependencies (Python):
#   uv add requests beautifulsoup4 lxml tqdm pydantic pdfminer.six spacy
#   uv run python -m spacy download en_core_web_sm
#
# Dependencies (System, Ubuntu):
#   sudo apt-get update
#   sudo apt-get install -y ocrmypdf tesseract-ocr ghostscript qpdf poppler-utils
#
# Usage:
#   # 1) Create a config
#   uv run python epstein_files_pipeline.py init-config --out ./config.json
#
#   # 2) Run pipeline
#   uv run python epstein_files_pipeline.py run --config ./config.json
#
#   # 3) Rebuild safe exports from existing entities/manifest
#   uv run python epstein_files_pipeline.py export-safe --config ./config.json
#
# Modification Log:
#   - 2025-12-19: Upgraded provenance + runs + chunk offsets + safe exports
# ============================================================================

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tqdm import tqdm

from pdfminer.high_level import extract_text as pdfminer_extract_text


# =============================================================================
# Configuration
# =============================================================================

class PipelineConfig(BaseModel):
    """Runtime configuration.

    IMPORTANT:
      - Keep seed URLs restricted to official sources.
      - allow_domains prevents accidental crawling of mirrors.
    """

    seed_urls: List[str] = Field(default_factory=list)
    output_dir: str = "./epstein_artifacts"
    allow_domains: List[str] = Field(
        default_factory=lambda: [
            "www.justice.gov",
            "justice.gov",
            "oversight.house.gov",
            "drive.google.com",
            "www.dropbox.com",
            "dropbox.com",
            "vault.fbi.gov",
            "www.fbi.gov",
        ]
    )

    # Download behavior
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) doc-pipeline/1.1"
    timeout_seconds: int = 60
    max_bytes_per_file: int = 2_000_000_000  # 2GB safety cap
    max_workers: int = 6
    polite_delay_seconds: float = 0.3
    verify_tls: bool = True

    # OCR behavior
    enable_ocr: bool = True
    ocrmypdf_lang: str = "eng"
    # Conservative defaults; tweak per corpus if needed.
    ocrmypdf_extra_args: List[str] = Field(default_factory=lambda: ["--skip-text", "--rotate-pages"])
    ocr_mode: str = "auto"  # auto|always|skip
    ocr_min_text_chars: int = 500

    # Chunking behavior
    chunk_chars: int = 10_000
    chunk_overlap_chars: int = 1_500

    # NER behavior
    spacy_model: str = "en_core_web_sm"

    # Optional basic redaction filters (defense-in-depth)
    redact_emails: bool = True
    redact_phones: bool = True
    redact_ssns: bool = True

    # Safe export controls
    safe_export_topn: int = 100


# =============================================================================
# Logging
# =============================================================================

def setup_logging(log_path: Path, verbose: bool = False) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# =============================================================================
# Utilities
# =============================================================================

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def safe_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("_")
    return name[:200] if len(name) > 200 else name


def url_domain(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url.strip())
    return (m.group(1).lower() if m else "")


def is_allowed(url: str, allow_domains: List[str]) -> bool:
    d = url_domain(url)
    return any(d == ad.lower() or d.endswith("." + ad.lower()) for ad in allow_domains)


def ensure_dirs(base: Path) -> Dict[str, Path]:
    paths = {
        "base": base,
        "downloads": base / "downloads",
        "ocr": base / "ocr",
        "text": base / "text",
        "chunks": base / "chunks",
        "entities": base / "entities",
        "safe_exports": base / "safe_exports",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def now_unix() -> int:
    return int(time.time())


def gen_run_id() -> str:
    # Time + randomness = unique enough; also makes runs sortable.
    return f"run_{int(time.time())}_{random.randint(1000, 9999)}"


def stable_config_hash(cfg: PipelineConfig) -> str:
    # Stable hash of config contents for run tracking.
    # Use model_dump_json with sorted keys (pydantic tends to be stable).
    return sha256_text(cfg.model_dump_json())


# =============================================================================
# Manifest + Run Tracking
# =============================================================================

@dataclass
class DownloadResult:
    url: str
    path: Path
    sha256: str  # doc_id
    bytes: int


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_manifest_index(manifest_path: Path) -> Dict[str, dict]:
    """Index manifest by sha256/doc_id.

    If duplicates exist, the last one wins.
    """
    idx: Dict[str, dict] = {}
    if not manifest_path.exists():
        return idx
    with manifest_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            doc_id = obj.get("sha256")
            if doc_id:
                idx[doc_id] = obj
    return idx


def doc_source_url(doc_id: str, downloads: List[DownloadResult], manifest_idx: Dict[str, dict]) -> str:
    for d in downloads:
        if d.sha256 == doc_id:
            return d.url
    if doc_id in manifest_idx:
        return str(manifest_idx[doc_id].get("url", ""))
    return ""


# =============================================================================
# Link discovery
# =============================================================================

PDF_HINTS = (".pdf", "/dl?inline=", "/dl?")


def discover_pdf_links(session: requests.Session, seed_url: str, allow_domains: List[str], timeout: int, verify_tls: bool) -> Set[str]:
    """Fetch a seed URL and extract PDF-ish links.

    Only returns links permitted by allow_domains.
    """

    logging.info(f"Discovering links from seed: {seed_url}")
    if not is_allowed(seed_url, allow_domains):
        logging.warning(f"Seed URL blocked by allowlist: {seed_url}")
        return set()

    resp = session.get(seed_url, timeout=timeout, verify=verify_tls)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        # Resolve relative links
        if href.startswith("/"):
            href = f"https://{url_domain(seed_url)}{href}"

        if not href.startswith("http"):
            continue

        h = href.lower()
        if any(hint in h for hint in PDF_HINTS):
            # Optional: if it's /dl? and doesn't mention pdf, still allow (DOJ media pages)
            if is_allowed(href, allow_domains):
                links.add(href)

    logging.info(f"Found {len(links)} candidate PDF links on {seed_url}")
    return links


# =============================================================================
# Download manager
# =============================================================================

SESSION_HEADERS = {}


def build_session(cfg: PipelineConfig) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": cfg.user_agent, **SESSION_HEADERS})
    return s


def _unique_download_name(url: str) -> str:
    """Stable name to avoid collisions when different URLs share the same filename."""
    base = safe_filename(url.split("?")[0].split("/")[-1] or "document.pdf")
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    prefix = hashlib.sha256(url.encode("utf-8", errors="replace")).hexdigest()[:10]
    return f"{prefix}__{base}"


def download_one(
    cfg: PipelineConfig,
    url: str,
    dest_dir: Path,
) -> DownloadResult:
    """Download a single URL to dest_dir with basic safety checks.

    Idempotency strategy:
      - Derive a stable unique filename from the URL.
      - If it exists and size > 0, reuse and hash.

    Notes:
      - Requests Sessions are not strictly guaranteed thread-safe.
        Each call creates its own session to be safe.
      - HTTP range resume can be added later if needed.
    """

    time.sleep(cfg.polite_delay_seconds)

    if not is_allowed(url, cfg.allow_domains):
        raise RuntimeError(f"URL blocked by allowlist: {url}")

    fname = _unique_download_name(url)
    out_path = dest_dir / fname

    if out_path.exists() and out_path.stat().st_size > 0:
        digest = sha256_file(out_path)
        return DownloadResult(url=url, path=out_path, sha256=digest, bytes=out_path.stat().st_size)

    s = build_session(cfg)
    with s.get(url, stream=True, timeout=cfg.timeout_seconds, verify=cfg.verify_tls, allow_redirects=True) as r:
        r.raise_for_status()

        # Redirect safety: final URL must still be allowlisted.
        final_url = str(r.url)
        if not is_allowed(final_url, cfg.allow_domains):
            raise RuntimeError(f"Redirected to blocked domain: {final_url}")

        total = 0
        tmp_path = out_path.with_suffix(out_path.suffix + ".part")

        with tmp_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                total += len(chunk)
                if total > cfg.max_bytes_per_file:
                    raise RuntimeError(f"File exceeds max_bytes safety cap ({cfg.max_bytes_per_file}): {url}")

        tmp_path.replace(out_path)

    digest = sha256_file(out_path)
    return DownloadResult(url=url, path=out_path, sha256=digest, bytes=total)


def download_all(cfg: PipelineConfig, downloads_dir: Path, pdf_urls: List[str]) -> Tuple[List[DownloadResult], List[dict]]:
    """Download all URLs concurrently.

    Returns:
      - successes: list[DownloadResult]
      - failures: list[dict]
    """

    successes: List[DownloadResult] = []
    failures: List[dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.max_workers) as ex:
        futures = {ex.submit(download_one, cfg, url, downloads_dir): url for url in pdf_urls}

        for fut in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Downloading"):
            url = futures[fut]
            try:
                res = fut.result()
                successes.append(res)
            except Exception as e:
                msg = str(e)
                logging.error(f"Download failed for {url}: {msg}")
                failures.append({"stage": "download", "url": url, "error": msg, "ts": now_unix()})

    return successes, failures


def append_manifest(manifest_path: Path, downloads: List[DownloadResult]) -> None:
    for d in downloads:
        append_jsonl(
            manifest_path,
            {
                "url": d.url,
                "path": str(d.path),
                "sha256": d.sha256,
                "bytes": d.bytes,
                "ts": now_unix(),
            },
        )


# =============================================================================
# OCR + Text Extraction
# =============================================================================

def has_tool(name: str) -> bool:
    return shutil.which(name) is not None


def should_ocr(pdf_path: Path, cfg: PipelineConfig) -> bool:
    if cfg.ocr_mode == "skip":
        return False
    if cfg.ocr_mode == "always":
        return True
    if cfg.ocr_mode == "auto":
        text = extract_text_pdf(pdf_path)
        return len(text.strip()) < cfg.ocr_min_text_chars
    # Fallback for unexpected modes: do not perform OCR or unnecessary text extraction.
    return False


def ocr_pdf(in_pdf: Path, out_pdf: Path, cfg: PipelineConfig) -> Tuple[bool, str]:
    """Run OCRmyPDF if available. Returns (success, message)."""

    if not has_tool("ocrmypdf"):
        return False, "ocrmypdf not found"

    cmd = [
        "ocrmypdf",
        "--language",
        cfg.ocrmypdf_lang,
        *cfg.ocrmypdf_extra_args,
        str(in_pdf),
        str(out_pdf),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return False, f"ocrmypdf failed: {proc.stderr.strip()[:800]}"
        return True, "ok"
    except Exception as e:
        return False, f"ocr exception: {e}"


def extract_text_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF. OCR greatly improves results for scanned docs."""
    try:
        return pdfminer_extract_text(str(pdf_path)) or ""
    except Exception as e:
        logging.error(f"pdfminer extraction failed for {pdf_path}: {e}")
        return ""


def write_text(out_path: Path, text: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", errors="replace")


# =============================================================================
# Redaction (basic)
# =============================================================================

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact_text(text: str, cfg: PipelineConfig) -> str:
    if cfg.redact_emails:
        text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    if cfg.redact_phones:
        text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    if cfg.redact_ssns:
        text = SSN_RE.sub("[REDACTED_SSN]", text)
    return text


# =============================================================================
# Chunking (overlap + offsets)
# =============================================================================

@dataclass
class Chunk:
    chunk_id: int
    char_start: int
    char_end: int
    text: str


def chunk_text_with_offsets(text: str, chunk_chars: int, overlap_chars: int) -> List[Chunk]:
    """Character-based chunking with overlap and offsets."""

    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be > 0")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be >= 0")

    chunks: List[Chunk] = []
    i = 0
    n = len(text)
    cid = 0

    while i < n:
        j = min(i + chunk_chars, n)
        chunk_text = text[i:j]
        chunks.append(Chunk(chunk_id=cid, char_start=i, char_end=j, text=chunk_text))
        cid += 1
        if j == n:
            break
        i = max(0, j - overlap_chars)

    return chunks


def write_chunks_jsonl(out_jsonl: Path, doc_id: str, source_url: str, chunks: List[Chunk]) -> None:
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for ch in chunks:
            preview = ch.text.replace("\n", " ").strip()
            if len(preview) > 240:
                preview = preview[:240] + "…"
            f.write(
                json.dumps(
                    {
                        "doc_id": doc_id,
                        "source_url": source_url,
                        "chunk_id": ch.chunk_id,
                        "char_start": ch.char_start,
                        "char_end": ch.char_end,
                        "preview": preview,
                        "text": ch.text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


# =============================================================================
# NER
# =============================================================================

def load_spacy(model_name: str):
    import spacy

    try:
        return spacy.load(model_name)
    except Exception as e:
        raise RuntimeError(
            f"spaCy model '{model_name}' not available. Install via: python -m spacy download {model_name}\nError: {e}"
        )


def ner_on_chunks(nlp, chunks: List[Chunk]) -> List[dict]:
    """Run NER over chunks and emit per-entity mention records.

    Output records are more useful than just counts because they retain provenance.
    """
    out: List[dict] = []
    for ch in chunks:
        doc = nlp(ch.text)
        for ent in doc.ents:
            t = ent.text.strip()
            if not t:
                continue
            out.append(
                {
                    "label": ent.label_,
                    "text": t,
                    "chunk_id": ch.chunk_id,
                    "char_start": ch.char_start,
                    "char_end": ch.char_end,
                }
            )
    return out


def write_entities_jsonl(out_jsonl: Path, doc_id: str, source_url: str, pdf_path: str, ent_mentions: List[dict]) -> None:
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for m in ent_mentions:
            f.write(
                json.dumps(
                    {
                        "doc_id": doc_id,
                        "source_url": source_url,
                        "pdf_path": pdf_path,
                        **m,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


# =============================================================================
# Safe exports (publishable-ish aggregates)
# =============================================================================

def aggregate_entities(entities_dir: Path, topn: int) -> Dict[str, List[dict]]:
    """Aggregate entity mentions across all docs into top-N lists per label."""

    counts: Dict[str, Dict[str, int]] = {}

    for p in entities_dir.glob("*.entities.jsonl"):
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                label = str(obj.get("label", ""))
                text = str(obj.get("text", "")).strip()
                if not label or not text:
                    continue
                counts.setdefault(label, {})[text] = counts[label].get(text, 0) + 1

    out: Dict[str, List[dict]] = {}
    for label, mp in counts.items():
        items = sorted(mp.items(), key=lambda x: (-x[1], x[0]))[:topn]
        out[label] = [{"text": t, "count": c} for t, c in items]
    return out


def write_safe_exports(paths: Dict[str, Path], cfg: PipelineConfig, manifest_path: Path) -> None:
    safe_dir = paths["safe_exports"]
    safe_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate entity mentions across corpus
    agg = aggregate_entities(paths["entities"], cfg.safe_export_topn)
    (safe_dir / "top_entities_by_label.json").write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")

    # Emit a sources list derived from manifest (publishable)
    sources: List[dict] = []
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                sources.append({"doc_id": obj.get("sha256"), "url": obj.get("url"), "bytes": obj.get("bytes"), "ts": obj.get("ts")})

    (safe_dir / "sources_from_manifest.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False), encoding="utf-8")


# =============================================================================
# Pipeline
# =============================================================================

def run_pipeline(cfg: PipelineConfig, verbose: bool = False) -> None:
    base = Path(cfg.output_dir).expanduser().resolve()
    paths = ensure_dirs(base)

    setup_logging(paths["base"] / "run.log", verbose=verbose)

    run_id = gen_run_id()
    cfg_hash = stable_config_hash(cfg)

    manifest_path = paths["base"] / "manifest.jsonl"
    runs_path = paths["base"] / "runs.jsonl"
    failures_path = paths["base"] / "failures.jsonl"

    logging.info(f"Run ID: {run_id}")
    logging.info(f"Config hash: {cfg_hash}")
    logging.info(f"Output base: {paths['base']}")

    run_metrics = {
        "run_id": run_id,
        "ts_start": now_unix(),
        "config_hash": cfg_hash,
        "seed_urls": cfg.seed_urls,
        "counts": {
            "seeds": len(cfg.seed_urls),
            "discovered_urls": 0,
            "download_success": 0,
            "download_failed": 0,
            "processed_docs": 0,
            "ocr_failed": 0,
            "text_empty": 0,
            "ner_failed": 0,
        },
    }

    failures: List[dict] = []

    # 1) Discover
    session = build_session(cfg)
    all_links: Set[str] = set()
    for seed in cfg.seed_urls:
        try:
            all_links |= discover_pdf_links(session, seed, cfg.allow_domains, cfg.timeout_seconds, cfg.verify_tls)
        except Exception as e:
            msg = str(e)
            logging.error(f"Discovery failed for {seed}: {msg}")
            failures.append({"stage": "discover", "url": seed, "error": msg, "ts": now_unix(), "run_id": run_id})

    pdf_urls = sorted(all_links)
    run_metrics["counts"]["discovered_urls"] = len(pdf_urls)
    logging.info(f"Total discovered PDF URLs: {len(pdf_urls)}")

    if not pdf_urls:
        logging.warning("No PDF URLs discovered. Add/verify seed URLs in config.")
        append_jsonl(runs_path, {**run_metrics, "ts_end": now_unix(), "status": "no_urls"})
        for fobj in failures:
            append_jsonl(failures_path, fobj)
        return

    # 2) Download
    downloads, download_failures = download_all(cfg, paths["downloads"], pdf_urls)
    run_metrics["counts"]["download_success"] = len(downloads)
    run_metrics["counts"]["download_failed"] = len(download_failures)

    # Record failures
    for fobj in download_failures:
        fobj["run_id"] = run_id
        failures.append(fobj)

    # Append manifest
    append_manifest(manifest_path, downloads)

    # Load manifest index (for provenance lookups)
    manifest_idx = load_manifest_index(manifest_path)

    # 3) OCR + 4) text + 5) chunk + 6) NER
    nlp = load_spacy(cfg.spacy_model)

    for d in tqdm(downloads, desc="Process PDFs"):
        doc_id = d.sha256
        source_url = d.url

        in_pdf = d.path

        try:
            # OCR
            ocr_pdf_path = paths["ocr"] / f"{doc_id}.ocr.pdf"
            effective_pdf_for_text = in_pdf

            if cfg.enable_ocr:
                if not ocr_pdf_path.exists() and should_ocr(in_pdf, cfg):
                    ok, msg = ocr_pdf(in_pdf, ocr_pdf_path, cfg)
                    if ok:
                        effective_pdf_for_text = ocr_pdf_path
                    else:
                        run_metrics["counts"]["ocr_failed"] += 1
                        logging.warning(f"OCR skipped/failed for {in_pdf.name}: {msg}")
                        failures.append({"stage": "ocr", "doc_id": doc_id, "url": source_url, "error": msg, "ts": now_unix(), "run_id": run_id})
                        effective_pdf_for_text = in_pdf
                elif ocr_pdf_path.exists():
                    effective_pdf_for_text = ocr_pdf_path

            # Extract text
            text = extract_text_pdf(effective_pdf_for_text)
            text = redact_text(text, cfg)

            if not text.strip():
                run_metrics["counts"]["text_empty"] += 1

            text_out = paths["text"] / f"{doc_id}.txt"
            write_text(text_out, text)

            # Chunk (with offsets)
            chunks = chunk_text_with_offsets(text, cfg.chunk_chars, cfg.chunk_overlap_chars)
            chunks_out = paths["chunks"] / f"{doc_id}.chunks.jsonl"
            write_chunks_jsonl(chunks_out, doc_id, source_url, chunks)

            # NER
            ent_mentions = ner_on_chunks(nlp, chunks)
            entities_out = paths["entities"] / f"{doc_id}.entities.jsonl"
            write_entities_jsonl(entities_out, doc_id, source_url, str(in_pdf), ent_mentions)

            run_metrics["counts"]["processed_docs"] += 1

        except Exception as e:
            msg = str(e)
            run_metrics["counts"]["ner_failed"] += 1
            logging.error(f"Processing failed for {in_pdf.name}: {msg}")
            failures.append({"stage": "process", "doc_id": doc_id, "url": source_url, "error": msg, "ts": now_unix(), "run_id": run_id})

    # 8) Safe exports
    try:
        write_safe_exports(paths, cfg, manifest_path)
    except Exception as e:
        msg = str(e)
        logging.warning(f"safe_exports generation failed: {msg}")
        failures.append({"stage": "safe_exports", "error": msg, "ts": now_unix(), "run_id": run_id})

    # Finalize run tracking
    run_metrics["ts_end"] = now_unix()
    run_metrics["status"] = "ok"
    append_jsonl(runs_path, run_metrics)

    for fobj in failures:
        append_jsonl(failures_path, fobj)

    logging.info("Pipeline complete.")


def rebuild_safe_exports(cfg: PipelineConfig, verbose: bool = False) -> None:
    base = Path(cfg.output_dir).expanduser().resolve()
    paths = ensure_dirs(base)
    setup_logging(paths["base"] / "run.log", verbose=verbose)

    manifest_path = paths["base"] / "manifest.jsonl"
    write_safe_exports(paths, cfg, manifest_path)
    logging.info("safe_exports regenerated.")


# =============================================================================
# CLI
# =============================================================================

def init_config(out_path: Path) -> None:
    """Write a starter config with reputable seed URLs.

    NOTE:
      - If a new official portal exists, add it to seed_urls.
      - Keep allow_domains strict.
    """

    starter = PipelineConfig(
        seed_urls=[
            "https://www.justice.gov/opa/",
            "https://vault.fbi.gov/jeffrey-epstein",
            "https://oversight.house.gov/",
        ],
    )

    out_path.write_text(starter.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote starter config: {out_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Download + OCR + chunk + NER pipeline for public document sets.")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging")

    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-config", help="Write a starter config JSON")
    p_init.add_argument("--out", required=True, help="Path to write config JSON")

    p_run = sub.add_parser("run", help="Run the pipeline")
    p_run.add_argument("--config", required=True, help="Path to config JSON")

    p_safe = sub.add_parser("export-safe", help="Regenerate safe exports from existing outputs")
    p_safe.add_argument("--config", required=True, help="Path to config JSON")

    return ap


def main() -> int:
    ap = build_arg_parser()
    args = ap.parse_args()

    if args.cmd == "init-config":
        init_config(Path(args.out))
        return 0

    cfg_path = Path(args.config)
    cfg = PipelineConfig.model_validate_json(cfg_path.read_text(encoding="utf-8"))

    if args.cmd == "run":
        run_pipeline(cfg, verbose=args.verbose)
        return 0

    if args.cmd == "export-safe":
        rebuild_safe_exports(cfg, verbose=args.verbose)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
