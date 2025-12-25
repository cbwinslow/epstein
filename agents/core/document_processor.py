#!/usr/bin/env python3
"""
Epstein Files Project - Consolidated Document Processor Agent

Unified document processing agent that consolidates functionality from:
- agents/epstein_data_processor.py
- epstein/epstein_files_pipeline.py

This agent provides a unified interface for document processing while
maintaining compatibility with the existing agent architecture.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from agents.base_agent import BaseAgent
from epstein.epstein_files_pipeline import EpsteinIngestionPipeline, PipelineConfig
from lib.resource_manager import get_resource_manager, WorkerType
from lib.observability_stack import get_observability_stack, trace_function, track_llm_call


# Configure logging
logger = logging.getLogger("epstein_document_processor")


class DocumentProcessorAgent(BaseAgent):
    """Consolidated document processing agent"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        
        # Initialize consolidated pipeline
        self.pipeline_config = PipelineConfig(
            download_dir=config.get("download_dir", "./downloads"),
            processed_dir=config.get("processed_dir", "./processed"),
            failed_dir=config.get("failed_dir", "./failed"),
            database_url=config.get("database_url"),
            max_workers=config.get("max_workers", 4),
            batch_size=config.get("batch_size", 10),
            ocr_enabled=config.get("ocr_enabled", True),
            ner_enabled=config.get("ner_enabled", True)
        )
        
        self.pipeline = EpsteinIngestionPipeline(self.pipeline_config)
        self.resource_manager = get_resource_manager()
        self.observability = get_observability_stack()
        
        # Initialize worker pool
        self._init_worker_pool()
        
        logger.info(f"🏗️  Document Processor Agent {agent_id} initialized")
    
    def _init_worker_pool(self):
        """Initialize worker pool for document processing"""
        try:
            # Create processing worker pool
            processing_config = {
                "pool_type": WorkerType.PROCESSING,
                "min_workers": self.config.get("min_workers", 2),
                "max_workers": self.config.get("max_workers", 8),
                "target_utilization": 0.7,
                "check_interval": 30.0
            }
            
            self.processing_pool = self.resource_manager.create_worker_pool(
                WorkerType.PROCESSING,
                processing_config
            )
            
            logger.info("✅ Processing worker pool initialized")
            
        except Exception as e:
            logger.error(f"❌ Worker pool initialization failed: {e}")
            raise
    
    @trace_function
    async def process_document(self, document_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a single document through the pipeline"""
        document_id = str(uuid4())
        
        try:
            logger.info(f"📄 Processing document: {Path(document_path).name}")
            
            # Submit to worker pool for processing
            future = self.processing_pool.submit_task(
                self._process_document_task,
                document_path,
                document_id,
                metadata or {}
            )
            
            # Wait for completion
            result = await asyncio.wrap_future(future)
            
            # Update metrics
            self.observability.metrics.documents_processed.inc(
                labels={'source': 'agent', 'status': 'success'}
            )
            
            logger.info(f"✅ Document {document_id} processed successfully")
            return result
            
        except Exception as e:
            # Update metrics for failed processing
            self.observability.metrics.documents_processed.inc(
                labels={'source': 'agent', 'status': 'failed'}
            )
            
            logger.error(f"❌ Document processing failed: {e}")
            raise
    
    async def _process_document_task(self, document_path: str, document_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Internal task for processing documents"""
        start_time = time.time()
        
        try:
            # Process document through pipeline
            result = await self.pipeline._process_single_document(
                document_path,
                source_id=metadata.get("source_id", "agent")
            )
            
            processing_time = time.time() - start_time
            
            # Update metrics
            self.observability.metrics.document_processing_time.observe(
                processing_time,
                labels={
                    'source': metadata.get("source_id", "agent"),
                    'document_type': metadata.get("document_type", "unknown")
                }
            )
            
            return {
                "document_id": document_id,
                "status": "completed",
                "processing_time": processing_time,
                "result": result
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Update metrics for failed processing
            self.observability.metrics.document_processing_time.observe(
                processing_time,
                labels={
                    'source': metadata.get("source_id", "agent"),
                    'document_type': metadata.get("document_type", "unknown")
                }
            )
            
            raise
    
    @trace_function
    async def process_batch(self, document_paths: List[str], batch_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a batch of documents"""
        batch_id = str(uuid4())
        results = []
        failed_count = 0
        
        try:
            logger.info(f"📦 Processing batch {batch_id} with {len(document_paths)} documents")
            
            # Submit all documents to worker pool
            futures = []
            for i, document_path in enumerate(document_paths):
                future = self.processing_pool.submit_task(
                    self._process_document_task,
                    document_path,
                    f"{batch_id}_{i}",
                    batch_metadata or {}
                )
                futures.append(future)
            
            # Wait for all tasks to complete
            for future in asyncio.as_completed(futures):
                try:
                    result = await future
                    results.append(result)
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Batch document processing failed: {e}")
            
            # Update batch metrics
            success_count = len(results)
            self.observability.metrics.documents_processed.inc(
                labels={'source': 'agent', 'status': 'success'},
                amount=success_count
            )
            self.observability.metrics.documents_processed.inc(
                labels={'source': 'agent', 'status': 'failed'},
                amount=failed_count
            )
            
            logger.info(f"✅ Batch {batch_id} completed: {success_count} success, {failed_count} failed")
            
            return {
                "batch_id": batch_id,
                "total_documents": len(document_paths),
                "successful": success_count,
                "failed": failed_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {e}")
            raise
    
    @trace_function
    async def extract_text(self, document_path: str, extraction_method: str = "auto") -> Dict[str, Any]:
        """Extract text from document"""
        try:
            # Use pipeline's text extraction
            pages_text, page_count, ocr_required = self.pipeline._extract_text_from_document(document_path)
            
            return {
                "document_path": document_path,
                "pages_text": pages_text,
                "page_count": page_count,
                "ocr_required": ocr_required,
                "extraction_method": extraction_method
            }
            
        except Exception as e:
            logger.error(f"❌ Text extraction failed: {e}")
            raise
    
    @trace_function
    @track_llm_call(model="gpt-3.5-turbo", provider="openrouter")
    async def analyze_document(self, document_text: str, analysis_type: str = "summary") -> Dict[str, Any]:
        """Analyze document content using AI"""
        try:
            # Use pipeline's AI analysis
            analysis = await self.pipeline._analyze_with_ai(
                model="gpt-3.5-turbo",
                document_text=document_text,
                analysis_type=analysis_type
            )
            
            return {
                "analysis_type": analysis_type,
                "result": analysis,
                "model": "gpt-3.5-turbo"
            }
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed: {e}")
            raise
    
    @trace_function
    async def extract_entities(self, document_text: str, page_number: int = 1) -> Dict[str, Any]:
        """Extract entities from document text"""
        try:
            # Use pipeline's NER
            entities = self.pipeline._perform_ner(document_text, page_number)
            
            return {
                "page_number": page_number,
                "entities": entities,
                "entity_count": len(entities)
            }
            
        except Exception as e:
            logger.error(f"❌ Entity extraction failed: {e}")
            raise
    
    @trace_function
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status and statistics"""
        try:
            # Get pipeline status
            pipeline_status = self.pipeline.get_status()
            
            # Get worker pool stats
            pool_stats = self.processing_pool.get_stats()
            
            # Get system stats
            system_stats = self.resource_manager.get_system_stats()
            
            return {
                "agent_id": self.agent_id,
                "status": self.status,
                "current_task": self.current_task,
                "pipeline_status": {
                    "run_id": pipeline_status.run_id,
                    "progress": pipeline_status.progress,
                    "files_processed": pipeline_status.files_processed,
                    "files_total": pipeline_status.files_total,
                    "errors": pipeline_status.errors
                },
                "worker_pool": pool_stats,
                "system": system_stats["system"],
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Status retrieval failed: {e}")
            raise
    
    async def handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent tasks"""
        task_type = task.get("type")
        payload = task.get("payload", {})
        
        try:
            if task_type == "process_document":
                return await self.process_document(
                    document_path=payload["document_path"],
                    metadata=payload.get("metadata")
                )
            
            elif task_type == "process_batch":
                return await self.process_batch(
                    document_paths=payload["document_paths"],
                    batch_metadata=payload.get("batch_metadata")
                )
            
            elif task_type == "extract_text":
                return await self.extract_text(
                    document_path=payload["document_path"],
                    extraction_method=payload.get("extraction_method", "auto")
                )
            
            elif task_type == "analyze_document":
                return await self.analyze_document(
                    document_text=payload["document_text"],
                    analysis_type=payload.get("analysis_type", "summary")
                )
            
            elif task_type == "extract_entities":
                return await self.extract_entities(
                    document_text=payload["document_text"],
                    page_number=payload.get("page_number", 1)
                )
            
            elif task_type == "get_status":
                return await self.get_status()
            
            else:
                raise ValueError(f"Unknown task type: {task_type}")
                
        except Exception as e:
            logger.error(f"❌ Task handling failed: {e}")
            return {
                "task_id": task.get("task_id"),
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def stop(self):
        """Stop the agent and cleanup resources"""
        try:
            # Stop worker pool
            if hasattr(self, 'processing_pool'):
                self.processing_pool.shutdown()
            
            # Stop pipeline
            if hasattr(self, 'pipeline'):
                # Pipeline cleanup handled by resource manager
            
            logger.info(f"🛑 Document Processor Agent {self.agent_id} stopped")
            
        except Exception as e:
            logger.error(f"❌ Agent shutdown failed: {e}")
            raise


# Backward compatibility wrapper
class EpsteinDataProcessorAgent(DocumentProcessorAgent):
    """Backward compatibility wrapper for existing epstein_data_processor.py"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        logger.warning("⚠️  EpsteinDataProcessorAgent is deprecated. Use DocumentProcessorAgent instead.")
        super().__init__(agent_id, config)


# Factory function for easy agent creation
def create_document_processor_agent(agent_id: str, config: Dict[str, Any] = None) -> DocumentProcessorAgent:
    """Create a document processor agent with default configuration"""
    default_config = {
        "download_dir": "./downloads",
        "processed_dir": "./processed", 
        "failed_dir": "./failed",
        "database_url": None,
        "max_workers": 4,
        "batch_size": 10,
        "ocr_enabled": True,
        "ner_enabled": True,
        "min_workers": 2
    }
    
    if config:
        default_config.update(config)
    
    return DocumentProcessorAgent(agent_id, default_config)


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def example():
        # Create agent
        agent = create_document_processor_agent("test_processor", {
            "max_workers": 2,
            "ocr_enabled": True
        })
        
        # Start agent
        await agent.start()
        
        # Process a document (if exists)
        try:
            result = await agent.process_document("./downloads/test.pdf")
            print(f"✅ Document processed: {result}")
        except FileNotFoundError:
            print("📝 Test document not found, skipping document processing")
        
        # Get status
        status = await agent.get_status()
        print(f"📊 Agent status: {status}")
        
        # Stop agent
        await agent.stop()
    
    # Run example
    asyncio.run(example())