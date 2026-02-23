#!/usr/bin/env python3
"""
Graph Population Pipeline Script

Consumes NER output from JSONL files in entities/ directory and populates
the Neo4j graph according to the knowledge graph schema.

Features:
- Aggregates entities across documents
- Creates Document and Entity nodes
- Establishes MENTIONED_IN relationships
- Uses Neo4j Python driver with batching for performance
- Includes comprehensive error handling and logging
"""

import json
import logging
import os
from collections import defaultdict
from pathlib import Path

from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Entity type mapping from NER labels to Neo4j node types
ENTITY_TYPE_MAPPING = {
    'PERSON': 'Person',
    'ORG': 'Organization',
    'ORGANIZATION': 'Organization',
    'LOC': 'Location',
    'LOCATION': 'Location',
    'GPE': 'Location',  # Geopolitical entity
    'MISC': 'Organization',  # Fallback
}

class GraphPopulationPipeline:
    def __init__(self, uri: str, user: str, password: str, entities_dir: str = "entities"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.entities_dir = Path(entities_dir)
        self.documents: dict[str, dict] = {}  # doc_id -> document data
        self.entities: defaultdict[tuple[str, str], list[dict]] = defaultdict(list)  # (label, text) -> list of mentions
        self.mention_counts: defaultdict[tuple[str, str], defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))  # (entity_key, doc_id) -> count

    def close(self):
        self.driver.close()

    def load_ner_data(self) -> None:
        """Load and parse all NER JSONL files from entities directory."""
        if not self.entities_dir.exists():
            raise FileNotFoundError(f"Entities directory not found: {self.entities_dir}")

        jsonl_files = list(self.entities_dir.glob("*.entities.jsonl"))
        if not jsonl_files:
            logger.warning(f"No .entities.jsonl files found in {self.entities_dir}")
            return

        logger.info(f"Found {len(jsonl_files)} entity files to process")

        for file_path in jsonl_files:
            logger.info(f"Processing {file_path}")
            try:
                with open(file_path, encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            self._process_entity_mention(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON at {file_path}:{line_num}: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

        logger.info(f"Loaded data for {len(self.documents)} documents and {len(self.entities)} unique entities")

    def _process_entity_mention(self, data: dict) -> None:
        """Process a single entity mention from JSONL."""
        doc_id = data.get('doc_id')
        if not doc_id:
            logger.warning("Entity mention missing doc_id, skipping")
            return

        # Store document info
        if doc_id not in self.documents:
            self.documents[doc_id] = {
                'id': doc_id,
                'title': data.get('pdf_path', doc_id),
                'source_url': data.get('source_url', ''),
                'type': 'court_filing',  # Default type
            }

        label = data.get('label')
        text = data.get('text')
        confidence = data.get('confidence', 0.0)

        if not label or not text:
            logger.warning(f"Entity mention missing label or text in doc {doc_id}, skipping")
            return

        # Normalize entity key
        entity_key = (label, text.strip())

        # Store mention
        self.entities[entity_key].append({
            'doc_id': doc_id,
            'confidence': confidence,
            'char_start': data.get('char_start'),
            'char_end': data.get('char_end'),
        })

        # Count mentions per entity per document
        self.mention_counts[entity_key][doc_id] += 1

    def aggregate_entities(self) -> dict[tuple[str, str], dict]:
        """Aggregate entity data across all mentions."""
        aggregated = {}

        for (label, text), mentions in self.entities.items():
            doc_ids = list(set(m['doc_id'] for m in mentions))
            confidences = [m['confidence'] for m in mentions if m['confidence'] > 0]

            aggregated[(label, text)] = {
                'id': f"{label}_{text.replace(' ', '_').lower()}",
                'name': text,
                'type': ENTITY_TYPE_MAPPING.get(label, 'Organization'),  # Default fallback
                'confidence_score': sum(confidences) / len(confidences) if confidences else 0.5,
                'source_documents': doc_ids,
            }

        return aggregated

    def populate_graph(self) -> None:
        """Populate the Neo4j graph with documents, entities, and relationships."""
        aggregated_entities = self.aggregate_entities()

        logger.info(f"Starting graph population with {len(self.documents)} documents and {len(aggregated_entities)} entities")

        # Create constraints if they don't exist
        self._create_constraints()

        # Batch process documents
        self._batch_create_documents()

        # Batch process entities
        self._batch_create_entities(aggregated_entities)

        # Batch create relationships
        self._batch_create_relationships(aggregated_entities)

        logger.info("Graph population completed successfully")

    def _create_constraints(self) -> None:
        """Create unique constraints for node IDs."""
        with self.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
                session.run("CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
                session.run("CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE")
                session.run("CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE")
                logger.info("Database constraints created/verified")
            except Exception as e:
                logger.error(f"Error creating constraints: {e}")

    def _batch_create_documents(self) -> None:
        """Create Document nodes in batches."""
        batch_size = 100
        documents_list = list(self.documents.values())

        for i in range(0, len(documents_list), batch_size):
            batch = documents_list[i:i + batch_size]
            with self.driver.session() as session:
                try:
                    session.execute_write(self._create_documents_tx, batch)
                    logger.info(f"Created batch of {len(batch)} documents")
                except Exception as e:
                    logger.error(f"Error creating document batch: {e}")

    @staticmethod
    def _create_documents_tx(tx, documents: list[dict]):
        """Transaction function to create Document nodes."""
        query = """
        UNWIND $documents AS doc
        MERGE (d:Document {id: doc.id})
        SET d.title = doc.title,
            d.type = doc.type,
            d.source_url = doc.source_url,
            d.confidence_score = 1.0,
            d.source_documents = [doc.id]
        """
        tx.run(query, documents=documents)

    def _batch_create_entities(self, aggregated_entities: dict[tuple[str, str], dict]) -> None:
        """Create Entity nodes in batches."""
        batch_size = 100
        entities_list = list(aggregated_entities.values())

        for i in range(0, len(entities_list), batch_size):
            batch = entities_list[i:i + batch_size]
            with self.driver.session() as session:
                try:
                    session.execute_write(self._create_entities_tx, batch)
                    logger.info(f"Created batch of {len(batch)} entities")
                except Exception as e:
                    logger.error(f"Error creating entity batch: {e}")

    @staticmethod
    def _create_entities_tx(tx, entities: list[dict]):
        """Transaction function to create Entity nodes."""
        for entity in entities:
            node_type = entity['type']
            query = f"""
            MERGE (e:{node_type} {{id: $id}})
            SET e.name = $name,
                e.confidence_score = $confidence_score,
                e.source_documents = $source_documents
            """
            tx.run(query, **entity)

    def _batch_create_relationships(self, aggregated_entities: dict[tuple[str, str], dict]) -> None:
        """Create MENTIONED_IN relationships in batches."""
        batch_size = 500
        relationships = []

        for (label, text), entity_data in aggregated_entities.items():
            entity_id = entity_data['id']
            node_type = entity_data['type']

            for doc_id in entity_data['source_documents']:
                frequency = self.mention_counts[(label, text)][doc_id]
                relationships.append({
                    'entity_id': entity_id,
                    'entity_type': node_type,
                    'doc_id': doc_id,
                    'frequency': frequency,
                })

        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]
            with self.driver.session() as session:
                try:
                    session.execute_write(self._create_relationships_tx, batch)
                    logger.info(f"Created batch of {len(batch)} relationships")
                except Exception as e:
                    logger.error(f"Error creating relationship batch: {e}")

    @staticmethod
    def _create_relationships_tx(tx, relationships: list[dict]):
        """Transaction function to create MENTIONED_IN relationships."""
        query = """
        UNWIND $relationships AS rel
        MATCH (e {id: rel.entity_id}), (d:Document {id: rel.doc_id})
        WHERE labels(e)[0] = rel.entity_type
        MERGE (e)-[m:MENTIONED_IN {mention_type: 'mentioned', frequency: rel.frequency}]->(d)
        SET m.confidence_score = 0.8,
            m.evidence = [rel.doc_id]
        """
        tx.run(query, relationships=relationships)

def main():
    """Main execution function."""
    # Configuration from environment variables
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    entities_dir = os.getenv('ENTITIES_DIR', 'entities')

    logger.info("Starting graph population pipeline")

    pipeline = GraphPopulationPipeline(neo4j_uri, neo4j_user, neo4j_password, entities_dir)

    try:
        pipeline.load_ner_data()
        pipeline.populate_graph()
        logger.info("Pipeline completed successfully")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise
    finally:
        pipeline.close()

if __name__ == "__main__":
    main()
