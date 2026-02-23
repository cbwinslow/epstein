#!/usr/bin/env python3
# ============================================================================
# Script Name: epstein_files_pipeline.py
# Date: 2025-12-19
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   End-to-end pipeline to:
#     1) Discover document URLs from trusted "seed" pages (DOJ / House Oversight)
#     2) Download PDFs with resume + checksum manifest
#     3) OCR PDFs into searchable PDFs (preferred: ocrmypdf) and extract text
#     4) Chunk text with overlap to preserve context boundaries
#     5) Run Named Entity Recognition (NER) and emit structured JSONL outputs
#
# Safety / Ethics Notes (IMPORTANT):
#   - This tool is intended for research on PUBLICLY RELEASED MATERIALS.
#   - Do not use outputs to accuse individuals of crimes; treat names as "mentioned"
#     unless a document explicitly alleges/charges and you can cite the source.
#   - Avoid re-publishing personal data (addresses, phones, victim identities).
#     Consider enabling redaction filters before sharing results.
#
# Inputs:
#   - A config JSON file (or CLI flags) specifying:
#       * seed_urls: pages to crawl for PDF links
#       * output_dir: where to store downloads and derived artifacts
#       * optional allow_domains: domain allowlist for link safety
#
# Outputs:
#   - downloads/          (original PDFs)
#   - ocr/                (OCR-processed PDFs)
#   - text/               (extracted text per PDF)
#   - entities/           (NER outputs per PDF + JSONL summaries)
#   - manifest.jsonl      (one line per file with sha256 + source URL)
#   - run.log             (pipeline log)
#
# Dependencies:
#   Python:
#     pip install -U requests beautifulsoup4 lxml tqdm pydantic "spacy>=3.7" pdfminer.six
#     python -m spacy download en_core_web_sm
#
#   System (recommended for best OCR results):
#     - ocrmypdf
#     - tesseract-ocr
#     - ghostscript
#     - qpdf
#
#   Ubuntu/Debian example:
#     sudo apt-get update
#     sudo apt-get install -y ocrmypdf tesseract-ocr ghostscript qpdf
#
# Usage:
#   1) Create a config:
#      python epstein_files_pipeline.py --init-config ./config.json
#   2) Edit config.json seeds (DOJ/oversight links) and run:
#      python epstein_files_pipeline.py --config ./config.json run
#
# Modification Log:
#   - 2025-12-19: Initial version
# ============================================================================

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# pdf text extraction (lightweight; works even without OCR, but OCR improves)
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pydantic import BaseModel, Field
from tqdm import tqdm

# -----------------------------
# Configuration / Models
# -----------------------------

class PipelineConfig(BaseModel):
    """Runtime configuration.

    Notes:
      - Keep seed URLs restricted to official sources.
      - allow_domains prevents accidental crawling of random mirrors.
    """

    seed_urls: list[str] = Field(default_factory=list)
    output_dir: str = "./epstein_artifacts"
    allow_domains: list[str] = Field(
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
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) epstein-pipeline/1.0"
    timeout_seconds: int = 60
    max_bytes_per_file: int = 2_000_000_000  # 2GB safety cap
    max_workers: int = 6
    polite_delay_seconds: float = 0.3

    # OCR behavior
    enable_ocr: bool = True
    ocrmypdf_lang: str = "eng"
    ocrmypdf_extra_args: list[str] = Field(default_factory=lambda: ["--skip-text", "--rotate-pages"])

    # NER behavior
    spacy_model: str = "en_core_web_sm"
    chunk_chars: int = 10_000
    chunk_overlap_chars: int = 1_500

    # Optional basic redaction filters (defense-in-depth before sharing)
    redact_emails: bool = True
    redact_phones: bool = True
    redact_ssns: bool = True


# -----------------------------
# Logging
# -----------------------------

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


# -----------------------------
# Utilities
# -----------------------------

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    # Collapse weird chars and keep it portable.
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("_")
    return name[:200] if len(name) > 200 else name


def url_domain(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url.strip())
    return (m.group(1).lower() if m else "")


def is_allowed(url: str, allow_domains: list[str]) -> bool:
    d = url_domain(url)
    return any(d == ad.lower() or d.endswith("." + ad.lower()) for ad in allow_domains)


def ensure_dirs(base: Path) -> dict[str, Path]:
    paths = {
        "base": base,
        "downloads": base / "downloads",
        "ocr": base / "ocr",
        "text": base / "text",
        "entities": base / "entities",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


# -----------------------------
# Link discovery
# -----------------------------

def discover_pdf_links(session: requests.Session, seed_url: str, allow_domains: list[str], timeout: int) -> set[str]:
    """Fetch a seed URL and extract direct PDF links.

    Handles:
      - Direct PDF links (.pdf)
      - DOJ dl?inline endpoints

    This function *only* returns links that match allow_domains.
    """

    logging.info(f"Discovering links from seed: {seed_url}")
    if not is_allowed(seed_url, allow_domains):
        logging.warning(f"Seed URL blocked by allowlist: {seed_url}")
        return set()

    resp = session.get(seed_url, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # Resolve relative links
        if href.startswith("/"):
            href = f"https://{url_domain(seed_url)}{href}"

        if not href.startswith("http"):
            continue

        # Keep PDFs and DOJ media download endpoints
        if (".pdf" in href.lower()) or ("/dl?inline=" in href.lower()) or ("/dl?" in href.lower() and "pdf" in href.lower()):
            if is_allowed(href, allow_domains):
                links.add(href)

    logging.info(f"Found {len(links)} candidate PDF links on {seed_url}")
    return links


# -----------------------------
# Download manager
# -----------------------------

@dataclass
class DownloadResult:
    url: str
    path: Path
    sha256: str
    bytes: int


def download_one(
    session: requests.Session,
    url: str,
    dest_dir: Path,
    timeout: int,
    max_bytes: int,
    polite_delay: float,
) -> DownloadResult:
    """Download a single URL to dest_dir with basic safety checks.

    Resume strategy:
      - If file exists and size > 0, we skip and hash it.
      - (If you want HTTP range resume, it can be added as a next step.)
    """

    time.sleep(polite_delay)

    # Try to derive a filename from URL
    fname = safe_filename(url.split("?")[0].split("/")[-1] or "document.pdf")
    if not fname.lower().endswith(".pdf"):
        fname += ".pdf"

    out_path = dest_dir / fname

    if out_path.exists() and out_path.stat().st_size > 0:
        digest = sha256_file(out_path)
        return DownloadResult(url=url, path=out_path, sha256=digest, bytes=out_path.stat().st_size)

    with session.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()

        total = 0
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                total += len(chunk)
                if total > max_bytes:
                    raise RuntimeError(f"File exceeds max_bytes safety cap ({max_bytes}): {url}")

    digest = sha256_file(out_path)
    return DownloadResult(url=url, path=out_path, sha256=digest, bytes=total)


def download_all(cfg: PipelineConfig, paths: dict[str, Path], pdf_urls: list[str]) -> list[DownloadResult]:
    session = requests.Session()
    session.headers.update({"User-Agent": cfg.user_agent})

    results: list[DownloadResult] = []

    # Threaded download with progress bar
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.max_workers) as ex:
        futures = {
            ex.submit(
                download_one,
                session,
                url,
                paths["downloads"],
                cfg.timeout_seconds,
                cfg.max_bytes_per_file,
                cfg.polite_delay_seconds,
            ): url
            for url in pdf_urls
        }

        for fut in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Downloading"):
            url = futures[fut]
            try:
                res = fut.result()
                results.append(res)
            except Exception as e:
                logging.error(f"Download failed for {url}: {e}")

    return results


def append_manifest(manifest_path: Path, downloads: list[DownloadResult]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as f:
        for d in downloads:
            f.write(
                json.dumps(
                    {
                        "url": d.url,
                        "path": str(d.path),
                        "sha256": d.sha256,
                        "bytes": d.bytes,
                        "ts": int(time.time()),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


# -----------------------------
# OCR + Text Extraction
# -----------------------------

def has_tool(name: str) -> bool:
    return shutil.which(name) is not None


def ocr_pdf(in_pdf: Path, out_pdf: Path, cfg: PipelineConfig) -> tuple[bool, str]:
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
            return False, f"ocrmypdf failed: {proc.stderr.strip()[:500]}"
        return True, "ok"
    except Exception as e:
        return False, f"ocr exception: {e}"


def extract_text_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF. If OCR was applied, this is usually much better."""
    try:
        return pdfminer_extract_text(str(pdf_path)) or ""
    except Exception as e:
        logging.error(f"pdfminer extraction failed for {pdf_path}: {e}")
        return ""


def write_text(out_path: Path, text: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", errors="replace")


# -----------------------------
# Chunking (overlap)
# -----------------------------

def chunk_text(text: str, chunk_chars: int, overlap_chars: int) -> list[str]:
    """Simple character-based chunking with overlap.

    Why chars?
      - Works without tokenizers
      - Deterministic and fast

    For LLM/RAG pipelines, you can swap this for token-based chunking later.
    """

    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be > 0")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be >= 0")

    chunks: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        j = min(i + chunk_chars, n)
        chunks.append(text[i:j])
        if j == n:
            break
        i = max(0, j - overlap_chars)

    return chunks


# -----------------------------
# Optional redaction filters (basic)
# -----------------------------

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


# -----------------------------
# NER
# -----------------------------

def load_spacy(model_name: str):
    import spacy

    try:
        return spacy.load(model_name)
    except Exception as e:
        raise RuntimeError(
            f"spaCy model '{model_name}' not available. Install via: python -m spacy download {model_name}\nError: {e}"
        )


def ner_on_chunks(nlp, chunks: list[str]) -> dict[str, int]:
    """Run NER over chunks and return entity counts by 'LABEL:TEXT'."""

    counts: dict[str, int] = {}
    for ch in chunks:
        doc = nlp(ch)
        for ent in doc.ents:
            key = f"{ent.label_}:{ent.text.strip()}"
            counts[key] = counts.get(key, 0) + 1
    return counts


def write_entities_jsonl(out_jsonl: Path, pdf_name: str, entity_counts: dict[str, int]) -> None:
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for k, c in sorted(entity_counts.items(), key=lambda x: (-x[1], x[0])):
            label, text = k.split(":", 1)
            f.write(json.dumps({"pdf": pdf_name, "label": label, "text": text, "count": c}, ensure_ascii=False) + "\n")


# -----------------------------
# Pipeline
# -----------------------------

def run_pipeline(cfg: PipelineConfig, verbose: bool = False) -> None:
    base = Path(cfg.output_dir).expanduser().resolve()
    paths = ensure_dirs(base)
    setup_logging(paths["base"] / "run.log", verbose=verbose)

    logging.info(f"Output base: {paths['base']}")

    # 1) Discover
    session = requests.Session()
    session.headers.update({"User-Agent": cfg.user_agent})

    all_links: set[str] = set()
    for seed in cfg.seed_urls:
        try:
            all_links |= discover_pdf_links(session, seed, cfg.allow_domains, cfg.timeout_seconds)
        except Exception as e:
            logging.error(f"Discovery failed for {seed}: {e}")

    pdf_urls = sorted(all_links)
    logging.info(f"Total discovered PDF URLs: {len(pdf_urls)}")

    if not pdf_urls:
        logging.warning("No PDF URLs discovered. Add/verify seed URLs in config.")
        return

    # 2) Download
    downloads = download_all(cfg, paths, pdf_urls)
    logging.info(f"Downloaded/verified files: {len(downloads)}")

    manifest_path = paths["base"] / "manifest.jsonl"
    append_manifest(manifest_path, downloads)

    # 3) OCR + text extraction + 4) chunking + 5) NER
    nlp = load_spacy(cfg.spacy_model)

    for d in tqdm(downloads, desc="Process PDFs"):
        in_pdf = d.path
        pdf_stem = in_pdf.stem

        # OCR
        ocr_pdf_path = paths["ocr"] / f"{pdf_stem}.ocr.pdf"
        if cfg.enable_ocr:
            if not ocr_pdf_path.exists():
                ok, msg = ocr_pdf(in_pdf, ocr_pdf_path, cfg)
                if not ok:
                    logging.warning(f"OCR skipped/failed for {in_pdf.name}: {msg}")
                    # fall back to original
                    ocr_pdf_path = in_pdf
            else:
                # already OCR'd
                pass
        else:
            ocr_pdf_path = in_pdf

        # Extract text
        text = extract_text_pdf(ocr_pdf_path)
        text = redact_text(text, cfg)  # defensive redaction before downstream analysis

        text_out = paths["text"] / f"{pdf_stem}.txt"
        write_text(text_out, text)

        # Chunk
        chunks = chunk_text(text, cfg.chunk_chars, cfg.chunk_overlap_chars)

        # NER
        entity_counts = ner_on_chunks(nlp, chunks)

        entities_out = paths["entities"] / f"{pdf_stem}.entities.jsonl"
        write_entities_jsonl(entities_out, in_pdf.name, entity_counts)

    logging.info("Pipeline complete.")


# -----------------------------
# CLI
# -----------------------------

def init_config(path: Path) -> None:
    """Write a starter config with reputable seed URLs.

    These seeds include official DOJ and House Oversight sources that have
    historically published Epstein-related document batches.

    NOTE: If DOJ releases a new portal today, add it to seed_urls.
    """

    starter = PipelineConfig(
        seed_urls=[
            # DOJ phase 1 press release (contains many direct document links)
            "https://www.justice.gov/opa/pr/attorney-general-pamela-bondi-releases-first-phase-declassified-epstein-files",
            # DOJ example media page with direct PDF link
            "https://www.justice.gov/ag/media/1391271",
            # House Oversight dump (links to Google Drive + Dropbox)
            "https://oversight.house.gov/release/oversight-committee-releases-additional-epstein-estate-documents/",
            # FBI Vault landing page (not always direct PDFs, but sometimes links out)
            "https://vault.fbi.gov/jeffrey-epstein",
        ],
    )

    path.write_text(starter.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote starter config: {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Download + OCR + NER pipeline for public document dumps.")
    ap.add_argument("--config", type=str, default="", help="Path to config JSON")
    ap.add_argument("--init-config", type=str, default="", help="Write a starter config JSON to this path")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging")

    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("run", help="Run the pipeline")

    args = ap.parse_args()

    if args.init_config:
        init_config(Path(args.init_config))
        return 0

    if args.cmd != "run":
        ap.print_help()
        return 2

    if not args.config:
        raise SystemExit("--config is required for run")

    cfg_path = Path(args.config)
    cfg = PipelineConfig.model_validate_json(cfg_path.read_text(encoding="utf-8"))

    run_pipeline(cfg, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ============================================================================
# OPTIONAL: TypeScript downloader sketch (if you prefer Node/TS)
# ============================================================================
# Save as download_epstein_docs.ts
#
#   npm i axios cheerio p-limit
#   npx ts-node download_epstein_docs.ts --seed <url> --out ./downloads
#
# ```ts
# import fs from "node:fs";
# import path from "node:path";
# import axios from "axios";
# import cheerio from "cheerio";
# import pLimit from "p-limit";
#
# const UA = "Mozilla/5.0 (X11; Linux x86_64) epstein-ts/1.0";
# const limit = pLimit(6);
#
# function isPdfLink(href: string) {
#   const h = href.toLowerCase();
#   return h.includes(".pdf") || h.includes("/dl?inline=");
# }
#
# async function discover(seed: string): Promise<string[]> {
#   const html = (await axios.get(seed, { headers: { "User-Agent": UA } })).data;
#   const $ = cheerio.load(html);
#   const links = new Set<string>();
#   $("a[href]").each((_, el) => {
#     let href = String($(el).attr("href") || "").trim();
#     if (!href) return;
#     if (href.startsWith("/")) href = new URL(href, seed).toString();
#     if (href.startsWith("http") && isPdfLink(href)) links.add(href);
#   });
#   return [...links];
# }
#
# async function download(url: string, outDir: string) {
#   const fname = path.basename(url.split("?")[0] || "document.pdf");
#   const out = path.join(outDir, fname.endsWith(".pdf") ? fname : `${fname}.pdf`);
#   if (fs.existsSync(out) && fs.statSync(out).size > 0) return out;
#   const resp = await axios.get(url, { responseType: "stream", headers: { "User-Agent": UA } });
#   await fs.promises.mkdir(outDir, { recursive: true });
#   await new Promise<void>((resolve, reject) => {
#     const w = fs.createWriteStream(out);
#     resp.data.pipe(w);
#     w.on("finish", () => resolve());
#     w.on("error", reject);
#   });
#   return out;
# }
#
# // Minimal CLI glue omitted for brevity — if you want, I’ll convert this into a
# // full standalone TS script with args, allowlist, hashing, and resume.
#
