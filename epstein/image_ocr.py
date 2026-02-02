#!/usr/bin/env python3
"""OCR utilities for image files using Tesseract."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class ImageOcrResult:
    image_path: Path
    text_path: Path
    success: bool
    message: str


def has_tool(tool: str) -> bool:
    return shutil.which(tool) is not None


def iter_images(input_dir: Path, extensions: Iterable[str]) -> List[Path]:
    exts = {ext.lower() for ext in extensions}
    images: List[Path] = []
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in exts:
            images.append(path)
    return images


def ocr_image(image_path: Path, output_dir: Path, lang: str = "eng") -> ImageOcrResult:
    if not has_tool("tesseract"):
        return ImageOcrResult(image_path, output_dir / f"{image_path.stem}.txt", False, "tesseract not found")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_base = output_dir / image_path.stem
    cmd = ["tesseract", str(image_path), str(output_base), "-l", lang]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "tesseract failed").strip()
        return ImageOcrResult(image_path, output_base.with_suffix(".txt"), False, msg)

    return ImageOcrResult(image_path, output_base.with_suffix(".txt"), True, "ok")


def run_image_ocr(
    input_dir: Path,
    output_dir: Path,
    extensions: Iterable[str],
    lang: str = "eng",
) -> Tuple[List[ImageOcrResult], List[ImageOcrResult]]:
    images = iter_images(input_dir, extensions)
    successes: List[ImageOcrResult] = []
    failures: List[ImageOcrResult] = []

    for image in images:
        result = ocr_image(image, output_dir, lang=lang)
        if result.success:
            successes.append(result)
        else:
            failures.append(result)

    return successes, failures


def main() -> int:
    ap = argparse.ArgumentParser(description="OCR image files into text outputs using Tesseract.")
    ap.add_argument("--input-dir", default="./epstein_artifacts/images")
    ap.add_argument("--output-dir", default="./epstein_artifacts/image_text")
    ap.add_argument("--lang", default="eng")
    ap.add_argument(
        "--extensions",
        default=".png,.jpg,.jpeg,.tif,.tiff",
        help="Comma-separated list of image extensions to OCR.",
    )
    args = ap.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    extensions = [ext.strip() for ext in args.extensions.split(",") if ext.strip()]

    if not input_dir.exists():
        raise SystemExit(f"Input dir not found: {input_dir}")

    successes, failures = run_image_ocr(input_dir, output_dir, extensions, lang=args.lang)

    print(f"[image-ocr] processed {len(successes) + len(failures)} images")
    if failures:
        print(f"[image-ocr] failures: {len(failures)}")
        for f in failures[:10]:
            print(f" - {f.image_path.name}: {f.message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
