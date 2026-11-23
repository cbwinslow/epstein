"""
Entity Extraction Agent
Specialized agent for advanced entity extraction, relationship mapping, and knowledge graph construction.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ExtractedEntity:
    """Represents an extracted entity"""

    entity_id: str
    entity_type: str
    text: str
    confidence: float
    start_pos: int
    end_pos: int
    context: str = ""


@dataclass
class EntityRelationship:
    """Represents a relationship between entities"""

    relationship_id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    confidence: float
    evidence: str = ""


class EntityExtractionAgent:
    """
    OpenAI-compatible agent for advanced entity extraction, relationship mapping,
    and knowledge graph construction.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.extracted_entities = {}
        self.entity_relationships = {}
        self.knowledge_graph = {}

    async def extract_entities(self, text: str, entity_types: list[str]) -> dict[str, Any]:
        """
        Extract entities of specified types from text.

        Args:
            text: Text content to analyze
            entity_types: List of entity types to extract

        Returns:
            Dictionary containing extracted entities
        """
        extraction_id = f"entities_{datetime.now().timestamp()}"

        try:
            # Simulate entity extraction
            await asyncio.sleep(2)  # Simulate processing time

            extracted_entities = []
            entity_map = {}

            # Mock entity extraction based on entity types
            for entity_type in entity_types:
                if entity_type == "PERSON":
                    entities = ["John Doe", "Jane Smith", "Robert Johnson"]
                elif entity_type == "ORG":
                    entities = ["Acme Corporation", "Global Tech", "Innovative Solutions"]
                elif entity_type == "LOC":
                    entities = ["New York", "San Francisco", "London"]
                elif entity_type == "DATE":
                    entities = ["2024-01-15", "2024-02-20", "2024-03-10"]
                else:
                    entities = [f"{entity_type}_1", f"{entity_type}_2"]

                for entity_text in entities:
                    entity_id = f"{entity_type.lower()}_{len(extracted_entities)}"
                    entity = ExtractedEntity(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        text=entity_text,
                        confidence=round(0.8 + (0.2 * (len(entities) % 5) / 5), 2),
                        start_pos=text.find(entity_text) if entity_text in text else 0,
                        end_pos=(
                            text.find(entity_text) + len(entity_text)
                            if entity_text in text
                            else len(entity_text)
                        ),
                        context=f"Context around {entity_text}",
                    )
                    extracted_entities.append(entity)
                    entity_map[entity_id] = entity

            self.extracted_entities[extraction_id] = entity_map

            result = {
                "extraction_id": extraction_id,
                "text_length": len(text),
                "entity_types": entity_types,
                "entities": [entity.__dict__ for entity in extracted_entities],
                "total_entities": len(extracted_entities),
                "timestamp": datetime.now().isoformat(),
            }

            return result

        except Exception as e:
            return {
                "extraction_id": extraction_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def extract_entity_relationships(
        self, text: str, entity_types: list[str]
    ) -> dict[str, Any]:
        """
        Extract relationships between entities in text.

        Args:
            text: Text content to analyze
            entity_types: List of entity types to consider for relationships

        Returns:
            Dictionary containing extracted entity relationships
        """
        extraction_id = f"relationships_{datetime.now().timestamp()}"

        try:
            # Simulate relationship extraction
            await asyncio.sleep(3)  # Simulate processing time

            # First extract entities if not already done
            entity_result = await self.extract_entities(text, entity_types)
            entities = entity_result.get("entities", [])

            relationships = []
            relationship_map = {}

            # Mock relationship extraction
            if len(entities) >= 2:
                for i in range(min(3, len(entities))):
                    for j in range(i + 1, min(i + 3, len(entities))):
                        source_entity = entities[i]["text"]
                        target_entity = entities[j]["text"]

                        relationship_id = f"rel_{len(relationships)}"
                        relationship = EntityRelationship(
                            relationship_id=relationship_id,
                            source_entity=source_entity,
                            target_entity=target_entity,
                            relationship_type="RELATED_TO",
                            confidence=round(0.7 + (0.3 * (i + j) / 10), 2),
                            evidence=f"Evidence linking {source_entity} and {target_entity}",
                        )
                        relationships.append(relationship)
                        relationship_map[relationship_id] = relationship

            self.entity_relationships[extraction_id] = relationship_map

            result = {
                "extraction_id": extraction_id,
                "text_length": len(text),
                "entity_types": entity_types,
                "relationships": [relationship.__dict__ for relationship in relationships],
                "total_relationships": len(relationships),
                "timestamp": datetime.now().isoformat(),
            }

            return result

        except Exception as e:
            return {
                "extraction_id": extraction_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def build_knowledge_graph(self, text: str, entity_types: list[str]) -> dict[str, Any]:
        """
        Build a knowledge graph from extracted entities and relationships.

        Args:
            text: Text content to analyze
            entity_types: List of entity types to include in the graph

        Returns:
            Dictionary containing knowledge graph structure
        """
        graph_id = f"kg_{datetime.now().timestamp()}"

        try:
            # Extract entities and relationships
            entity_result = await self.extract_entities(text, entity_types)
            relationship_result = await self.extract_entity_relationships(text, entity_types)

            entities = entity_result.get("entities", [])
            relationships = relationship_result.get("relationships", [])

            # Build knowledge graph structure
            nodes = []
            edges = []

            for entity in entities:
                nodes.append(
                    {
                        "id": entity["entity_id"],
                        "label": entity["text"],
                        "type": entity["entity_type"],
                        "confidence": entity["confidence"],
                    }
                )

            for relationship in relationships:
                edges.append(
                    {
                        "id": relationship["relationship_id"],
                        "source": relationship["source_entity"],
                        "target": relationship["target_entity"],
                        "type": relationship["relationship_type"],
                        "confidence": relationship["confidence"],
                        "evidence": relationship["evidence"],
                    }
                )

            knowledge_graph = {
                "nodes": nodes,
                "edges": edges,
                "statistics": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "density": round(len(edges) / len(nodes) if nodes else 0, 2),
                    "average_confidence": round(
                        (
                            sum(r["confidence"] for r in relationships) / len(relationships)
                            if relationships
                            else 0
                        ),
                        2,
                    ),
                },
            }

            self.knowledge_graph[graph_id] = knowledge_graph

            result = {
                "graph_id": graph_id,
                "text_length": len(text),
                "entity_types": entity_types,
                "knowledge_graph": knowledge_graph,
                "timestamp": datetime.now().isoformat(),
            }

            return result

        except Exception as e:
            return {
                "graph_id": graph_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_extraction_result(self, extraction_id: str) -> dict[str, Any]:
        """Get the result of a specific entity extraction."""
        result = self.extracted_entities.get(extraction_id)
        if not result:
            return {"error": "Extraction not found", "extraction_id": extraction_id}

        return {"entities": [entity.__dict__ for entity in result.values()]}

    def get_knowledge_graph(self, graph_id: str) -> dict[str, Any]:
        """Get a specific knowledge graph."""
        graph = self.knowledge_graph.get(graph_id)
        if not graph:
            return {"error": "Knowledge graph not found", "graph_id": graph_id}

        return graph


# OpenAI-compatible function definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_entities",
            "description": "Extract entities of specified types from text content",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text content to analyze for entities",
                    },
                    "entity_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entity types to extract (PERSON, ORG, LOC, DATE, etc.)",
                        "default": ["PERSON", "ORG", "LOC", "DATE"],
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_entity_relationships",
            "description": "Extract relationships between entities in text content",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text content to analyze for entity relationships",
                    },
                    "entity_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entity types to consider for relationships",
                        "default": ["PERSON", "ORG", "LOC"],
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_knowledge_graph",
            "description": "Build a knowledge graph from extracted entities and relationships",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text content to analyze for knowledge graph construction",
                    },
                    "entity_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entity types to include in the knowledge graph",
                        "default": ["PERSON", "ORG", "LOC"],
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_extraction_result",
            "description": "Get the result of a specific entity extraction",
            "parameters": {
                "type": "object",
                "properties": {
                    "extraction_id": {
                        "type": "string",
                        "description": "ID of the extraction to retrieve",
                    }
                },
                "required": ["extraction_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_graph",
            "description": "Get a specific knowledge graph by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "graph_id": {
                        "type": "string",
                        "description": "ID of the knowledge graph to retrieve",
                    }
                },
                "required": ["graph_id"],
            },
        },
    },
]


# Agent metadata
AGENT_INFO = {
    "name": "Entity Extraction Agent",
    "description": "Specialized agent for advanced entity extraction, relationship mapping, and knowledge graph construction",
    "version": "1.0.0",
    "capabilities": [
        "Entity extraction",
        "Relationship mapping",
        "Knowledge graph construction",
        "Named entity recognition",
        "Semantic analysis",
    ],
    "tools": TOOLS,
}


if __name__ == "__main__":
    # Example usage
    agent = EntityExtractionAgent()

    async def main():
        sample_text = "John Doe works at Acme Corporation in New York. Jane Smith is the CEO of Global Tech based in San Francisco."

        # Test entity extraction
        entities_result = await agent.extract_entities(sample_text, ["PERSON", "ORG", "LOC"])
        print("Entity extraction:", json.dumps(entities_result, indent=2))

        # Test relationship extraction
        relationships_result = await agent.extract_entity_relationships(
            sample_text, ["PERSON", "ORG"]
        )
        print("Relationship extraction:", json.dumps(relationships_result, indent=2))

        # Test knowledge graph construction
        kg_result = await agent.build_knowledge_graph(sample_text, ["PERSON", "ORG", "LOC"])
        print("Knowledge graph:", json.dumps(kg_result, indent=2))

    asyncio.run(main())
