#!/usr/bin/env python3
"""
GovInfo.gov Bulk Downloader for Epstein Document Analysis Pipeline

This module provides enhanced bulk downloading capabilities for govinfo.gov documents
with improved pagination, retry logic, and batch processing.
"""

import argparse
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


@dataclass
class GovInfoConfig:
    """Configuration for GovInfo.gov downloader"""

    base_url: str = "https://www.govinfo.gov"
    bulk_api_url: str = "https://www.govinfo.gov/bulkdata/bulkdata"
    collections_url: str = "https://www.govinfo.gov/bulkdata"
    user_agent: str = "Mozilla/5.0 (compatible; EpsteinPipeline/1.0)"
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 5
    batch_size: int = 100
    output_dir: str = "./downloads"


@dataclass
class GovInfoDocument:
    """Represents a document from govinfo.gov"""

    package_id: str
    title: str
    granule_id: str | None = None
    granule_title: str | None = None
    download_url: str
    file_size: int | None = None
    publish_date: str | None = None
    collection: str | None = None


class GovInfoDownloader:
    """Enhanced bulk downloader for govinfo.gov with pagination and retry logic"""

    def __init__(self, config: GovInfoConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})
        self.logger = logging.getLogger(__name__)

    def discover_collections(self) -> list[dict]:
        """Discover available collections from govinfo.gov"""
        try:
            response = self.session.get(
                self.config.collections_url, timeout=self.config.timeout_seconds
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            collections = []

            # Look for collection links/tables
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "bulkdata" in href and "collection" in href.lower():
                    title = link.get_text("").strip()
                    if title:
                        collections.append(
                            {
                                "name": title,
                                "url": f"https://www.govinfo.gov{href}",
                                "id": href.split("/")[-1] if href else "",
                            }
                        )

            self.logger.info(f"Discovered {len(collections)} collections")
            return collections

        except Exception as e:
            self.logger.error(f"Failed to discover collections: {e}")
            return []

    def get_collection_packages(self, collection_url: str) -> list[GovInfoDocument]:
        """Get all packages from a collection with pagination support"""
        packages = []
        offset = 0
        total_found = 0

        with tqdm(desc=f"Fetching packages from {collection_url}") as pbar:
            while True:
                try:
                    # Try bulk API first
                    bulk_url = (
                        f"{self.config.bulk_api_url}?collection={collection_url.split('/')[-1]}"
                    )
                    if offset > 0:
                        bulk_url += f"&offset={offset}"

                    response = self._make_request(bulk_url)
                    if not response:
                        break

                    data = response.json()

                    if "packages" in data:
                        batch_packages = []
                        for pkg_data in data["packages"]:
                            doc = GovInfoDocument(
                                package_id=pkg_data.get("packageId", ""),
                                title=pkg_data.get("title", ""),
                                granule_id=pkg_data.get("granuleId"),
                                granule_title=pkg_data.get("granuleTitle"),
                                download_url=pkg_data.get("downloadUrl", ""),
                                file_size=pkg_data.get("size"),
                                publish_date=pkg_data.get("publishDate"),
                                collection=pkg_data.get("collectionName"),
                            )
                            batch_packages.append(doc)

                        packages.extend(batch_packages)
                        total_found += len(batch_packages)
                        pbar.update(len(batch_packages))

                        # Check if there are more results
                        if len(batch_packages) < self.config.batch_size:
                            break

                        offset += self.config.batch_size

                    else:
                        self.logger.warning(f"No packages found in response from {bulk_url}")
                        break

                except Exception as e:
                    self.logger.error(f"Error fetching batch from {collection_url}: {e}")
                    break

        self.logger.info(f"Total packages discovered: {len(packages)}")
        return packages

    def download_document(self, doc: GovInfoDocument, output_dir: Path) -> bool:
        """Download a single document with retry logic"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate safe filename
        safe_title = re.sub(r"[^\w\s\-_\.]", "_", doc.title)
        filename = f"{doc.package_id}_{safe_title}.pdf"
        filepath = output_dir / filename

        # Skip if already exists and has reasonable size
        if filepath.exists() and filepath.stat().st_size > 1000:  # At least 1KB
            self.logger.debug(f"Skipping existing file: {filename}")
            return True

        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Downloading {doc.title} (attempt {attempt + 1})")

                response = self.session.get(
                    doc.download_url, timeout=self.config.timeout_seconds, stream=True
                )
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))

                with (
                    open(filepath, "wb") as f,
                    tqdm(
                        total=total_size, unit="B", unit_scale=True, desc=filename[:50], leave=False
                    ) as pbar,
                ):
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

                self.logger.info(f"Successfully downloaded: {filename}")
                return True

            except Exception as e:
                self.logger.warning(f"Download attempt {attempt + 1} failed for {doc.title}: {e}")

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    self.logger.error(
                        f"Failed to download {doc.title} after {self.config.max_retries} attempts"
                    )
                    return False

        return False

    def download_collection(self, collection: dict, output_dir: Path) -> tuple[int, int]:
        """Download all documents from a collection"""
        collection_name = collection.get("name", "unknown")
        collection_url = collection.get("url", "")

        self.logger.info(f"Starting download for collection: {collection_name}")

        # Get all packages
        packages = self.get_collection_packages(collection_url)
        if not packages:
            self.logger.warning(f"No packages found for collection: {collection_name}")
            return 0, 0

        # Create collection subdirectory
        collection_dir = output_dir / collection_name
        success_count = 0
        failure_count = 0

        for doc in tqdm(packages, desc=f"Downloading {collection_name}"):
            if self.download_document(doc, collection_dir):
                success_count += 1
            else:
                failure_count += 1

        self.logger.info(
            f"Collection {collection_name} complete: {success_count} success, {failure_count} failures"
        )
        return success_count, failure_count

    def download_all_collections(self, output_dir: Path) -> dict[str, tuple[int, int]]:
        """Download all available collections"""
        collections = self.discover_collections()
        if not collections:
            self.logger.error("No collections discovered")
            return {}

        results = {}

        for collection in tqdm(collections, desc="Processing collections"):
            collection_name = collection.get("name", "unknown")
            success, failure = self.download_collection(collection, output_dir)
            results[collection_name] = (success, failure)

        return results

    def _make_request(self, url: str, method: str = "GET") -> requests.Response | None:
        """Make HTTP request with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, timeout=self.config.timeout_seconds)
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request attempt {attempt + 1} failed for {url}: {e}")

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    self.logger.error(
                        f"Request failed after {self.config.max_retries} attempts: {url}"
                    )
                    return None

        return None


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )


def save_download_report(results: dict[str, tuple[int, int]], output_path: Path):
    """Save a comprehensive download report"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "collections": results,
        "summary": {
            "total_collections": len(results),
            "total_successes": sum(success for success, _ in results.values()),
            "total_failures": sum(failure for _, failure in results.values()),
        },
    }

    with open(output_path / "download_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Enhanced GovInfo.gov Bulk Downloader")
    parser.add_argument(
        "--output-dir", "-o", default="./downloads", help="Output directory for downloads"
    )
    parser.add_argument(
        "--collections",
        "-c",
        help="Comma-separated list of collection names to download (default: all)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--report-only", action="store_true", help="Only generate report, do not download"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = GovInfoConfig(output_dir=str(output_dir))
    downloader = GovInfoDownloader(config)

    if args.report_only:
        # Just discover and report
        collections = downloader.discover_collections()
        print(f"Discovered {len(collections)} collections:")
        for coll in collections:
            print(f"  - {coll['name']}: {coll['url']}")
        return

    # Download collections
    if args.collections:
        # Download specific collections
        target_collections = [c.strip() for c in args.collections.split(",")]
        all_collections = downloader.discover_collections()

        # Filter to target collections
        [coll for coll in all_collections if coll["name"] in target_collections]
    else:
        # Download all collections
        downloader.discover_collections()

    results

    results = downloader.download_all_collections(output_dir)

    # Save comprehensive report
    save_download_report(results, output_dir)

    # Print summary
    total_successes = sum(success for success, _ in results.values())
    total_failures = sum(failure for _, failure in results.values())

    print(f"\n{'='*60}")
    print("Download Summary:")
    print(f"  Collections processed: {len(results)}")
    print(f"  Successful downloads: {total_successes}")
    print(f"  Failed downloads: {total_failures}")
    print(f"  Success rate: {total_successes/(total_successes + total_failures)*100:.1f}%")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
