#!/usr/bin/env python3
"""
Epstein Files Document Ingestion Pipeline

Comprehensive pipeline for processing Epstein-related documents from download
through OCR, NER, and database storage.

Features:
- Document discovery and download
- OCR processing for scanned documents
- Text extraction and normalization
- Named Entity Recognition (NER)
- Database integration
- Error handling and recovery
- Progress tracking and reporting
"""

import argparse
import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import pdfplumber
import pytesseract
import spacy
from bs4 import BeautifulSoup
from PIL import Image
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("epstein_ingestion")


# ============================================================================
# Configuration and Data Models
# ============================================================================


@dataclass
class PipelineConfig:
    """Configuration for ingestion pipeline"""

    download_dir: str = "./downloads"
    processed_dir: str = "./processed"
    failed_dir: str = "./failed"
    database_url: str | None = None
    max_workers: int = 4
    batch_size: int = 10
    ocr_enabled: bool = True
    ner_enabled: bool = True
    language: str = "en"

    # OCR settings
    ocr_dpi: int = 300
    ocr_language: str = "eng"
    ocr_timeout: int = 60

    # NER settings
    ner_model: str = "en_core_web_lg"
    ner_confidence_threshold: float = 0.5


@dataclass
class DocumentMetadata:
    """Metadata for processed documents"""

    document_id: str
    source_id: str
    ingestion_run_id: str
    file_path: str
    file_name: str
    file_size: int
    file_hash: str
    mime_type: str
    language: str
    page_count: int
    ocr_required: bool
    ocr_confidence: float | None
    processing_status: str
    error_message: str | None
    metadata: dict[str, Any]


@dataclass
class ExtractedText:
    """Extracted text from documents"""

    document_id: str
    page_number: int
    text_content: str
    extraction_method: str
    confidence_score: float | None
    language: str
    metadata: dict[str, Any]


@dataclass
class ExtractedEntity:
    """Named entity extracted from text"""

    document_id: str
    extracted_text_id: str | None
    entity_type: str
    entity_text: str
    confidence_score: float
    start_position: int
    end_position: int
    page_number: int
    metadata: dict[str, Any]


@dataclass
class IngestionRun:
    """Information about ingestion run"""

    run_id: str
    source_id: str
    status: str
    started_at: float
    completed_at: float | None
    files_processed: int
    files_total: int
    bytes_processed: int
    error_count: int
    config: dict[str, Any]
    metadata: dict[str, Any]


class PipelineStatus(BaseModel):
    """Current pipeline status"""

    run_id: str
    status: str
    progress: float
    files_processed: int
    files_total: int
    errors: int
    start_time: float
    current_time: float
    estimated_completion: float | None


# ============================================================================
# Ingestion Pipeline Implementation
# ============================================================================


class EpsteinIngestionPipeline:
    """Main document ingestion pipeline"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.run_id = str(uuid4())
        self.status = "initialized"
        self.start_time = time.time()
        self.processed_count = 0
        self.error_count = 0
        self.total_files = 0

        # Initialize directories
        self._init_directories()

        # Load NER model
        self._load_ner_model()

        # Initialize database connection
        self.db_connection = None
        if config.database_url:
            self._init_database()

        logger.info(f"🚀 Ingestion pipeline initialized (Run ID: {self.run_id})")

    def _init_directories(self):
        """Initialize required directories"""
        Path(self.config.download_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.processed_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.failed_dir).mkdir(parents=True, exist_ok=True)

        logger.debug("📁 Directories initialized:")
        logger.debug(f"   Downloads: {self.config.download_dir}")
        logger.debug(f"   Processed: {self.config.processed_dir}")
        logger.debug(f"   Failed: {self.config.failed_dir}")

    def _load_ner_model(self):
        """Load NER model if enabled"""
        if self.config.ner_enabled:
            try:
                self.ner_model = spacy.load(self.config.ner_model)
                logger.info(f"🤖 NER model loaded: {self.config.ner_model}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load NER model: {e}")
                self.config.ner_enabled = False
        else:
            self.ner_model = None

    def _init_database(self):
        """Initialize database connection"""
        try:
            import psycopg2
            from psycopg2.extras import DictCursor

            self.db_connection = psycopg2.connect(
                self.config.database_url, cursor_factory=DictCursor
            )
            logger.info("🗄️  Database connection established")

            # Ensure schema is ready
            self._ensure_schema()

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.db_connection = None

    def _ensure_schema(self):
        """Ensure database schema is ready"""
        try:
            with self.db_connection.cursor() as cur:
                # Check if sources table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'sources'
                    )
                """)
                if not cur.fetchone()[0]:
                    logger.warning("⚠️  Database schema not found. Please run migrations first.")
                    return

                logger.info("✅ Database schema verified")

        except Exception as e:
            logger.error(f"❌ Schema verification failed: {e}")

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate file hash for deduplication"""
        hash_func = hashlib.sha256()

        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    def _get_mime_type(self, file_path: str) -> str:
        """Determine file MIME type"""
        import mimetypes

        import magic

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            try:
                mime_type = magic.from_file(file_path, mime=True)
            except:
                mime_type = "application/octet-stream"

        return mime_type

    def _detect_language(self, text: str) -> str:
        """Detect text language"""
        try:
            from langdetect import detect

            return detect(text) if text.strip() else self.config.language
        except:
            return self.config.language

    def _extract_text_from_pdf(self, file_path: str) -> tuple[list[str], int]:
        """Extract text from PDF using pdfplumber"""
        pages_text = []
        page_count = 0

        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)

                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                    else:
                        # Try OCR if text extraction fails
                        pages_text.append("")

            return pages_text, page_count

        except Exception as e:
            logger.warning(f"⚠️  PDF text extraction failed: {e}")
            return [], 0

    def _extract_text_from_image(self, file_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Convert to high resolution for better OCR
            image = Image.open(file_path)
            image = image.convert("L")  # Convert to grayscale

            # Use pytesseract for OCR
            text = pytesseract.image_to_string(
                image, lang=self.config.ocr_language, config=f"--dpi {self.config.ocr_dpi} --psm 6"
            )

            return text.strip()

        except Exception as e:
            logger.error(f"❌ OCR failed for {file_path}: {e}")
            return ""

    def _extract_text_from_html(self, file_path: str) -> str:
        """Extract text from HTML"""
        try:
            with open(file_path, encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            return soup.get_text(separator="\n", strip=True)

        except Exception as e:
            logger.error(f"❌ HTML extraction failed: {e}")
            return ""

    def _extract_text_from_document(self, file_path: str) -> tuple[list[str], int, bool]:
        """Extract text from document based on file type"""
        file_ext = Path(file_path).suffix.lower()
        pages_text = []
        page_count = 1
        ocr_required = False

        try:
            if file_ext == ".pdf":
                pages_text, page_count = self._extract_text_from_pdf(file_path)
                if not any(pages_text):
                    ocr_required = True

            elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
                text = self._extract_text_from_image(file_path)
                pages_text = [text] if text else [""]
                ocr_required = True

            elif file_ext in [".html", ".htm"]:
                text = self._extract_text_from_html(file_path)
                pages_text = [text] if text else [""]

            elif file_ext == ".txt":
                with open(file_path, encoding="utf-8") as f:
                    pages_text = [f.read()]

            else:
                logger.warning(f"⚠️  Unsupported file type: {file_ext}")
                pages_text = [""]

            return pages_text, page_count, ocr_required

        except Exception as e:
            logger.error(f"❌ Text extraction failed for {file_path}: {e}")
            return [], 1, False

    def _perform_ocr_if_needed(
        self, file_path: str, pages_text: list[str]
    ) -> tuple[list[str], float]:
        """Perform OCR on pages that need it"""
        if not self.config.ocr_enabled:
            return pages_text, None

        ocr_pages = []
        ocr_confidence = 0.0

        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext == ".pdf":
                # Convert PDF to images and OCR
                from pdf2image import convert_from_path

                images = convert_from_path(
                    file_path, dpi=self.config.ocr_dpi, timeout=self.config.ocr_timeout
                )

                for i, image in enumerate(images):
                    if i < len(pages_text) and not pages_text[i].strip():
                        text = pytesseract.image_to_string(image, lang=self.config.ocr_language)
                        ocr_pages.append(text)

                        # Estimate confidence (simplified)
                        if len(text) > 100:
                            ocr_confidence += 0.9
                        elif len(text) > 50:
                            ocr_confidence += 0.7
                        else:
                            ocr_confidence += 0.5
                    else:
                        ocr_pages.append(pages_text[i])

                # Average confidence
                if images:
                    ocr_confidence = min(1.0, ocr_confidence / len(images))

            return ocr_pages, ocr_confidence

        except Exception as e:
            logger.error(f"❌ OCR processing failed: {e}")
            return pages_text, None

    def _perform_ner(self, text: str, page_number: int) -> list[ExtractedEntity]:
        """Perform Named Entity Recognition on text"""
        if not self.config.ner_enabled or not self.ner_model:
            return []

        entities = []

        try:
            doc = self.ner_model(text)

            for ent in doc.ents:
                if ent.label_ and ent.text.strip():
                    entity = ExtractedEntity(
                        document_id="",  # Will be set later
                        extracted_text_id=None,
                        entity_type=ent.label_,
                        entity_text=ent.text,
                        confidence_score=(
                            min(1.0, ent._.confidence + 0.1)
                            if hasattr(ent._, "confidence")
                            else 0.8
                        ),
                        start_position=ent.start_char,
                        end_position=ent.end_char,
                        page_number=page_number,
                        metadata={"language": self.config.language, "model": self.config.ner_model},
                    )
                    entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"❌ NER failed: {e}")
            return []

    def _store_document_metadata(self, metadata: DocumentMetadata) -> str | None:
        """Store document metadata in database"""
        if not self.db_connection:
            return None

        try:
            with self.db_connection.cursor() as cur:
                # Insert or update source
                cur.execute(
                    """
                    INSERT INTO sources (name, type, description, config)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """,
                    (
                        metadata.source_id,
                        "govinfo",
                        f"Source: {metadata.source_id}",
                        json.dumps({"source_type": "govinfo"}),
                    ),
                )

                # Get source ID
                cur.execute("SELECT id FROM sources WHERE name = %s", (metadata.source_id,))
                source_result = cur.fetchone()
                if not source_result:
                    raise Exception("Source not found")
                source_id = source_result[0]

                # Insert ingestion run
                cur.execute(
                    """
                    INSERT INTO ingestion_runs
                    (source_id, status, started_at, files_processed, files_total, config, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
                """,
                    (
                        source_id,
                        "running",
                        metadata.ingestion_run_id,
                        0,
                        0,
                        json.dumps({"pipeline": "epstein_ingestion"}),
                        json.dumps({}),
                    ),
                )

                # Insert document
                cur.execute(
                    """
                    INSERT INTO documents
                    (source_id, ingestion_run_id, external_id, title, description,
                     file_path, file_name, file_size, file_hash, mime_type,
                     language, page_count, is_image_only, ocr_required,
                     ocr_confidence, processing_status, error_message, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_hash) DO NOTHING
                    RETURNING id
                """,
                    (
                        source_id,
                        metadata.ingestion_run_id,
                        metadata.document_id,
                        metadata.title or "Untitled",
                        metadata.description or "",
                        metadata.file_path,
                        metadata.file_name,
                        metadata.file_size,
                        metadata.file_hash,
                        metadata.mime_type,
                        metadata.language,
                        metadata.page_count,
                        metadata.mime_type.startswith("image/"),
                        metadata.ocr_required,
                        metadata.ocr_confidence,
                        metadata.processing_status,
                        metadata.error_message,
                        json.dumps(metadata.metadata or {}),
                    ),
                )

                result = cur.fetchone()
                if result:
                    self.db_connection.commit()
                    return str(result[0])

            return None

        except Exception as e:
            self.db_connection.rollback()
            logger.error(f"❌ Database error: {e}")
            return None

    def _store_extracted_text(self, text_data: ExtractedText) -> str | None:
        """Store extracted text in database"""
        if not self.db_connection:
            return None

        try:
            with self.db_connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO extracted_text
                    (document_id, page_number, text_content, extraction_method,
                     confidence_score, language, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_id, page_number) DO NOTHING
                    RETURNING id
                """,
                    (
                        text_data.document_id,
                        text_data.page_number,
                        text_data.text_content,
                        text_data.extraction_method,
                        text_data.confidence_score,
                        text_data.language,
                        json.dumps(text_data.metadata or {}),
                    ),
                )

                result = cur.fetchone()
                if result:
                    self.db_connection.commit()
                    return str(result[0])

            return None

        except Exception as e:
            self.db_connection.rollback()
            logger.error(f"❌ Text storage error: {e}")
            return None

    def _store_extracted_entities(self, entities: list[ExtractedEntity]) -> int:
        """Store extracted entities in database"""
        if not self.db_connection or not entities:
            return 0

        try:
            with self.db_connection.cursor() as cur:
                stored_count = 0

                for entity in entities:
                    cur.execute(
                        """
                        INSERT INTO entities
                        (document_id, extracted_text_id, entity_type, entity_text,
                         confidence_score, start_position, end_position, page_number, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (document_id, entity_type, entity_text, page_number) DO NOTHING
                    """,
                        (
                            entity.document_id,
                            entity.extracted_text_id,
                            entity.entity_type,
                            entity.entity_text,
                            entity.confidence_score,
                            entity.start_position,
                            entity.end_position,
                            entity.page_number,
                            json.dumps(entity.metadata or {}),
                        ),
                    )
                    stored_count += cur.rowcount

                self.db_connection.commit()
                return stored_count

        except Exception as e:
            self.db_connection.rollback()
            logger.error(f"❌ Entity storage error: {e}")
            return 0

    def _move_file_to_processed(self, file_path: str) -> str:
        """Move file to processed directory"""
        try:
            dest_path = Path(self.config.processed_dir) / Path(file_path).name
            if not dest_path.exists():
                Path(file_path).rename(dest_path)
            return str(dest_path)
        except Exception as e:
            logger.error(f"❌ Failed to move processed file: {e}")
            return file_path

    def _move_file_to_failed(self, file_path: str) -> str:
        """Move file to failed directory"""
        try:
            dest_path = Path(self.config.failed_dir) / Path(file_path).name
            if not dest_path.exists():
                Path(file_path).rename(dest_path)
            return str(dest_path)
        except Exception as e:
            logger.error(f"❌ Failed to move failed file: {e}")
            return file_path

    def _get_status(self) -> PipelineStatus:
        """Get current pipeline status"""
        current_time = time.time()
        elapsed = current_time - self.start_time

        estimated_completion = None
        if self.total_files > 0 and self.processed_count > 0:
            rate = self.processed_count / elapsed
            remaining = self.total_files - self.processed_count
            estimated_completion = current_time + (remaining / rate) if rate > 0 else None

        return PipelineStatus(
            run_id=self.run_id,
            status=self.status,
            progress=(self.processed_count / self.total_files * 100) if self.total_files > 0 else 0,
            files_processed=self.processed_count,
            files_total=self.total_files,
            errors=self.error_count,
            start_time=self.start_time,
            current_time=current_time,
            estimated_completion=estimated_completion,
        )

    async def _process_single_document(self, file_path: str, source_id: str) -> bool:
        """Process a single document through the pipeline"""
        start_time = time.time()
        document_id = str(uuid4())

        try:
            # 1. File analysis
            file_size = Path(file_path).stat().st_size
            file_hash = self._get_file_hash(file_path)
            mime_type = self._get_mime_type(file_path)

            logger.info(f"📄 Processing document: {Path(file_path).name}")

            # 2. Text extraction
            pages_text, page_count, ocr_required = self._extract_text_from_document(file_path)

            # 3. OCR if needed
            if ocr_required and self.config.ocr_enabled:
                pages_text, ocr_confidence = self._perform_ocr_if_needed(file_path, pages_text)
            else:
                ocr_confidence = None

            # 4. Language detection
            if pages_text:
                sample_text = " ".join([t[:100] for t in pages_text if t.strip()][:3])
                language = self._detect_language(sample_text)
            else:
                language = self.config.language

            # 5. Create document metadata
            document_metadata = DocumentMetadata(
                document_id=document_id,
                source_id=source_id,
                ingestion_run_id=self.run_id,
                file_path=file_path,
                file_name=Path(file_path).name,
                file_size=file_size,
                file_hash=file_hash,
                mime_type=mime_type,
                language=language,
                page_count=page_count,
                ocr_required=ocr_required,
                ocr_confidence=ocr_confidence,
                processing_status="text_extracted",
                error_message=None,
                metadata={
                    "source": source_id,
                    "pipeline_run": self.run_id,
                    "processing_time": time.time() - start_time,
                },
            )

            # 6. Store document metadata
            stored_doc_id = self._store_document_metadata(document_metadata)
            if not stored_doc_id:
                logger.warning("⚠️  Failed to store document metadata")
                document_metadata.processing_status = "failed"
                document_metadata.error_message = "Database storage failed"

            # 7. Store extracted text
            text_entries = []
            for i, text_content in enumerate(pages_text):
                if text_content.strip():
                    text_entry = ExtractedText(
                        document_id=stored_doc_id or document_id,
                        page_number=i + 1,
                        text_content=text_content,
                        extraction_method="ocr" if ocr_required else "native",
                        confidence_score=ocr_confidence,
                        language=language,
                        metadata={"source": source_id, "page": i + 1, "total_pages": page_count},
                    )
                    text_entries.append(text_entry)

                    stored_text_id = self._store_extracted_text(text_entry)
                    if stored_text_id:
                        text_entry.extracted_text_id = stored_text_id

            # 8. Perform NER on extracted text
            all_entities = []
            for i, text_content in enumerate(pages_text):
                if text_content.strip():
                    entities = self._perform_ner(text_content, i + 1)
                    for entity in entities:
                        entity.document_id = stored_doc_id or document_id
                        entity.extracted_text_id = (
                            text_entries[i].extracted_text_id if i < len(text_entries) else None
                        )
                    all_entities.extend(entities)

            # 9. Store extracted entities
            if all_entities:
                stored_entity_count = self._store_extracted_entities(all_entities)
                logger.info(f"🏷️  Extracted {stored_entity_count} entities")

            # 10. Update document status
            if stored_doc_id:
                with self.db_connection.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE documents
                        SET processing_status = %s, entity_count = %s
                        WHERE id = %s
                    """,
                        ("completed", len(all_entities), stored_doc_id),
                    )
                    self.db_connection.commit()

            # 11. Move to processed directory
            processed_path = self._move_file_to_processed(file_path)
            document_metadata.file_path = processed_path

            # 12. Update counters
            self.processed_count += 1
            logger.info(f"✅ Successfully processed: {Path(file_path).name}")

            return True

        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Processing failed for {file_path}: {e}")

            # Move to failed directory
            self._move_file_to_failed(file_path)

            return False

    async def _discover_documents(self, source_dir: str) -> list[str]:
        """Discover documents to process"""
        documents = []

        try:
            for file_path in Path(source_dir).glob("*"):
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()
                    if file_ext in [
                        ".pdf",
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".tiff",
                        ".bmp",
                        ".html",
                        ".htm",
                        ".txt",
                    ]:
                        documents.append(str(file_path))

            logger.info(f"🔍 Discovered {len(documents)} documents for processing")
            return documents

        except Exception as e:
            logger.error(f"❌ Document discovery failed: {e}")
            return []

    async def run_pipeline(self, source_dir: str | None = None, source_id: str = "govinfo"):
        """Run the complete ingestion pipeline"""
        self.status = "running"
        source_dir = source_dir or self.config.download_dir

        try:
            # 1. Discover documents
            documents = await self._discover_documents(source_dir)
            self.total_files = len(documents)

            if not documents:
                logger.warning("⚠️  No documents found for processing")
                self.status = "completed"
                return False

            logger.info(f"🚀 Starting ingestion pipeline (Run ID: {self.run_id})")
            logger.info(f"📄 Total documents to process: {self.total_files}")

            # 2. Process documents in batches
            for i in range(0, len(documents), self.config.batch_size):
                batch = documents[i : i + self.config.batch_size]

                # Process batch concurrently
                tasks = [self._process_single_document(doc, source_id) for doc in batch]
                await asyncio.gather(*tasks)

                # Update status
                status = self._get_status()
                logger.info(
                    f"📊 Progress: {status.progress:.1f}% ({status.files_processed}/{status.files_total})"
                )

                # Small delay between batches to avoid overwhelming system
                await asyncio.sleep(0.1)

            # 3. Complete ingestion run
            if self.db_connection:
                with self.db_connection.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE ingestion_runs
                        SET status = %s, completed_at = %s,
                            files_processed = %s, error_count = %s
                        WHERE id = %s
                    """,
                        (
                            "completed",
                            time.time(),
                            self.processed_count,
                            self.error_count,
                            self.run_id,
                        ),
                    )
                    self.db_connection.commit()

            # 4. Final status
            self.status = "completed"
            final_status = self._get_status()

            logger.info("🎉 Ingestion pipeline completed!")
            logger.info(f"   Processed: {final_status.files_processed} documents")
            logger.info(f"   Errors: {final_status.errors}")
            logger.info(f"   Time: {time.time() - self.start_time:.1f} seconds")

            return True

        except Exception as e:
            self.status = "failed"
            logger.error(f"❌ Pipeline failed: {e}")
            return False

        finally:
            # Cleanup
            if self.db_connection:
                self.db_connection.close()

    def get_status(self) -> PipelineStatus:
        """Get current pipeline status"""
        return self._get_status()


# ============================================================================
# Command Line Interface
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Epstein Files Document Ingestion Pipeline")

    parser.add_argument(
        "--source-dir", default="./downloads", help="Directory containing documents to process"
    )

    parser.add_argument("--source-id", default="govinfo", help="Source identifier for documents")

    parser.add_argument("--database-url", help="Database connection URL")

    parser.add_argument("--max-workers", type=int, default=4, help="Maximum concurrent workers")

    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for processing")

    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR processing")

    parser.add_argument("--no-ner", action="store_true", help="Disable NER processing")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Configure pipeline
    config = PipelineConfig(
        download_dir=args.source_dir,
        database_url=args.database_url,
        max_workers=args.max_workers,
        batch_size=args.batch_size,
        ocr_enabled=not args.no_ocr,
        ner_enabled=not args.no_ner,
    )

    # Create and run pipeline
    pipeline = EpsteinIngestionPipeline(config)

    # Run pipeline
    success = asyncio.run(pipeline.run_pipeline(args.source_dir, args.source_id))

    if not success:
        logger.error("❌ Pipeline completed with errors")
        return 1

    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        logger.info("🛑 Pipeline interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        exit(1)
