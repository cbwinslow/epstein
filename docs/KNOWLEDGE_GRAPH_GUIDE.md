# Knowledge Graph Implementation Guide

**Version**: 1.0  
**Last Updated**: 2025-12-31  
**Status**: Planning & Design Phase

## Overview

This document provides a comprehensive guide for implementing a knowledge graph system for the Epstein document analysis pipeline. The knowledge graph will represent entities (people, organizations, locations, events) and their relationships extracted from documents.

## Table of Contents

1. [Objectives](#objectives)
2. [Architecture](#architecture)
3. [Graph Database Selection](#graph-database-selection)
4. [Schema Design](#schema-design)
5. [Implementation Plan](#implementation-plan)
6. [Query Patterns](#query-patterns)
7. [Integration](#integration)
8. [Best Practices](#best-practices)

---

## Objectives

### Primary Goals

1. **Unified Entity Representation**: Create a single source of truth for all entities across documents
2. **Relationship Discovery**: Enable sophisticated queries to discover connections between entities
3. **Temporal Analysis**: Support time-based queries and relationship evolution
4. **Evidence Traceability**: Maintain provenance links from graph to source documents
5. **Scalability**: Handle 10,000+ entities and 50,000+ relationships efficiently
6. **Query Performance**: Return typical queries in <2 seconds

### Use Cases

- Find all connections between two people
- Identify common associates of multiple entities
- Discover travel patterns and co-travelers
- Map organizational relationships
- Build timeline of entity interactions
- Detect communities and clusters
- Find anomalous or unexpected relationships

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   Documents     │
│   (PDF, Text)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  NER Pipeline   │
│  (spaCy, etc.)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│  (entities,     │
│  relationships) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Graph Builder  │
│  (ETL Process)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Graph Database  │
│ (Neo4j/AGE)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Query API      │
│  (GraphQL/REST) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Visualization   │
│ & Analysis UI   │
└─────────────────┘
```

### Components

1. **NER Pipeline**: Extracts entities and relationships from documents
2. **PostgreSQL**: Stores raw entity and relationship data with provenance
3. **Graph Builder**: ETL process to populate graph from PostgreSQL
4. **Graph Database**: Stores graph structure optimized for traversal queries
5. **Query API**: Provides programmatic access to graph
6. **Visualization**: Interactive graph exploration and analysis

---

## Graph Database Selection

### Evaluation Criteria

1. **Open Source**: Prefer open source with active community
2. **Query Performance**: Fast graph traversal and pattern matching
3. **Python Support**: Excellent Python driver and library support
4. **Scalability**: Handle expected graph size (10K-100K nodes)
5. **PostgreSQL Integration**: Good integration with existing PostgreSQL data
6. **Learning Curve**: Reasonable learning curve for team
7. **Deployment**: Easy to deploy with Docker

### Options Considered

#### Option 1: Neo4j (Community Edition)

**Pros:**
- Industry-leading graph database
- Cypher query language is powerful and intuitive
- Excellent visualization tools (Neo4j Browser, Bloom)
- Great documentation and community
- Mature Python driver (neo4j-driver)
- Built-in graph algorithms library

**Cons:**
- Community edition has some limitations
- Separate database from PostgreSQL (data duplication)
- Can be resource-intensive

**Use Case Fit**: ⭐⭐⭐⭐⭐ Excellent

#### Option 2: Apache AGE (A Graph Extension for PostgreSQL)

**Pros:**
- Runs inside PostgreSQL as an extension
- No separate database needed
- Can query both relational and graph data together
- Cypher-like query language (openCypher)
- Leverages existing PostgreSQL infrastructure

**Cons:**
- Relatively new project
- Smaller community than Neo4j
- Less mature tooling
- Limited visualization options

**Use Case Fit**: ⭐⭐⭐⭐ Very Good

#### Option 3: RedisGraph

**Pros:**
- Very fast query performance
- Lightweight and fast to deploy
- Good Python support
- Cypher query language

**Cons:**
- In-memory (Redis) may have size limitations
- Less sophisticated than Neo4j
- Smaller community

**Use Case Fit**: ⭐⭐⭐ Good

### Recommendation: Neo4j Community Edition

**Decision**: Use Neo4j Community Edition for the following reasons:

1. **Maturity**: Most mature graph database with proven track record
2. **Tooling**: Best-in-class visualization and development tools
3. **Query Language**: Cypher is powerful and well-documented
4. **Community**: Large community and extensive resources
5. **Graph Algorithms**: Built-in algorithms for community detection, centrality, etc.
6. **Integration**: Good Python support via official driver

**Trade-off**: Accept data duplication between PostgreSQL and Neo4j in exchange for superior graph capabilities.

**Architecture Decision Record**: See `docs/ADR/001-graph-database-selection.md`

---

## Schema Design

### Node Types

#### Person Node
```cypher
(:Person {
  id: String,                    // Unique identifier
  name: String,                  // Canonical name
  aliases: [String],             // Alternative names, nicknames
  birth_date: Date,              // Birth date (if known)
  nationality: String,           // Nationality
  occupation: String,            // Primary occupation
  created_at: DateTime,          // When added to graph
  updated_at: DateTime,          // Last update
  confidence: Float,             // Overall confidence score (0-1)
  source_count: Integer          // Number of source documents
})
```

#### Organization Node
```cypher
(:Organization {
  id: String,
  name: String,
  aliases: [String],
  type: String,                  // Company, Foundation, Government, etc.
  location: String,              // Primary location
  founding_date: Date,
  dissolution_date: Date,
  created_at: DateTime,
  updated_at: DateTime,
  confidence: Float,
  source_count: Integer
})
```

#### Location Node
```cypher
(:Location {
  id: String,
  name: String,
  type: String,                  // Property, City, Country, Island, etc.
  coordinates: Point,            // Geo coordinates
  address: String,
  country: String,
  created_at: DateTime,
  updated_at: DateTime,
  confidence: Float,
  source_count: Integer
})
```

#### Event Node
```cypher
(:Event {
  id: String,
  type: String,                  // Meeting, Flight, Transaction, etc.
  date: DateTime,
  end_date: DateTime,            // For multi-day events
  location_id: String,
  description: String,
  created_at: DateTime,
  updated_at: DateTime,
  confidence: Float,
  source_count: Integer
})
```

#### Document Node
```cypher
(:Document {
  id: String,
  title: String,
  date: Date,
  source: String,                // DOJ, FBI, etc.
  url: String,
  checksum: String,
  page_count: Integer,
  created_at: DateTime
})
```

### Edge Types (Relationships)

#### KNOWS Relationship
```cypher
(p1:Person)-[:KNOWS {
  start_date: Date,              // When relationship began
  end_date: Date,                // When relationship ended (if known)
  relationship_type: String,     // Friend, Associate, Employee, etc.
  confidence: Float,
  source_docs: [String],         // Document IDs
  evidence_count: Integer,
  first_seen: DateTime,          // First mentioned in documents
  last_seen: DateTime            // Last mentioned in documents
}]->(p2:Person)
```

#### EMPLOYED_BY Relationship
```cypher
(p:Person)-[:EMPLOYED_BY {
  start_date: Date,
  end_date: Date,
  role: String,                  // Job title
  department: String,
  confidence: Float,
  source_docs: [String]
}]->(o:Organization)
```

#### TRAVELED_WITH Relationship
```cypher
(p1:Person)-[:TRAVELED_WITH {
  date: Date,
  flight_number: String,
  aircraft: String,
  departure: String,
  destination: String,
  confidence: Float,
  source_docs: [String]
}]->(p2:Person)
```

#### ATTENDED Relationship
```cypher
(p:Person)-[:ATTENDED {
  role: String,                  // Host, Guest, Speaker, etc.
  confirmed: Boolean,
  confidence: Float,
  source_docs: [String]
}]->(e:Event)
```

#### OWNS / OWNED Relationship
```cypher
(p:Person)-[:OWNS {
  start_date: Date,
  end_date: Date,
  ownership_type: String,        // Full, Partial, Beneficial
  percentage: Float,
  confidence: Float,
  source_docs: [String]
}]->(l:Location)
```

#### COMMUNICATED_WITH Relationship
```cypher
(p1:Person)-[:COMMUNICATED_WITH {
  start_date: Date,
  end_date: Date,
  medium: String,                // Email, Phone, In-Person
  frequency: String,             // Regular, Occasional, Rare
  message_count: Integer,
  confidence: Float,
  source_docs: [String]
}]->(p2:Person)
```

#### MENTIONED_IN Relationship
```cypher
(entity)-[:MENTIONED_IN {
  page: Integer,
  paragraph: Integer,
  sentence: Integer,
  chunk_id: String,
  context: String,               // Surrounding text
  confidence: Float
}]->(d:Document)
```

### Indexes and Constraints

```cypher
// Unique constraints
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;

// Indexes for frequent queries
CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name);
CREATE INDEX location_name IF NOT EXISTS FOR (l:Location) ON (l.name);
CREATE INDEX event_date IF NOT EXISTS FOR (e:Event) ON (e.date);
CREATE INDEX doc_source IF NOT EXISTS FOR (d:Document) ON (d.source);

// Full-text search indexes
CREATE FULLTEXT INDEX person_search IF NOT EXISTS FOR (p:Person) ON EACH [p.name, p.aliases];
CREATE FULLTEXT INDEX org_search IF NOT EXISTS FOR (o:Organization) ON EACH [o.name, o.aliases];
```

---

## Implementation Plan

### Phase 1: Setup & Basic Infrastructure (Week 1-2)

**Tasks:**
1. Deploy Neo4j Docker container
2. Install Python driver: `pip install neo4j`
3. Create initial schema with constraints and indexes
4. Build basic connection and query utilities
5. Write unit tests for database operations

**Deliverables:**
- Neo4j running in Docker Compose
- Python connection library
- Schema creation scripts
- Basic CRUD operations tested

### Phase 2: ETL Pipeline (Week 3-4)

**Tasks:**
1. Extract entities from PostgreSQL `entities` table
2. Create/update Person, Organization, Location nodes
3. Handle entity disambiguation and deduplication
4. Extract relationships from PostgreSQL
5. Create edges with appropriate types
6. Link entities to source documents

**Deliverables:**
- ETL scripts in `scripts/graph_etl.py`
- Idempotent graph population
- Progress tracking and logging
- Error handling and recovery

### Phase 3: Core Queries (Week 5-6)

**Tasks:**
1. Implement essential query patterns
2. Create query templates library
3. Add query performance optimization
4. Build query API endpoint
5. Write comprehensive query tests

**Deliverables:**
- Query library in `epstein/graph/queries.py`
- REST API for graph queries
- Query documentation
- Performance benchmarks

### Phase 4: Entity Resolution (Week 7-8)

**Tasks:**
1. Implement name normalization
2. Build fuzzy matching for duplicates
3. Create entity clustering
4. Develop merge candidate detection
5. Build resolution review UI (optional)

**Deliverables:**
- Entity resolution module
- Merge candidate reports
- Resolution statistics
- Updated graph with merged entities

### Phase 5: Visualization (Week 9-10)

**Tasks:**
1. Select visualization library (Cytoscape.js or D3.js)
2. Build graph rendering component
3. Add interactive features (zoom, filter, search)
4. Implement layout algorithms
5. Create export functionality

**Deliverables:**
- Interactive graph viewer
- Integration with query API
- Export to PNG/SVG/GraphML
- User documentation

### Phase 6: Advanced Analysis (Week 11-12)

**Tasks:**
1. Implement graph algorithms (centrality, communities)
2. Build path analysis tools
3. Create pattern matching queries
4. Add temporal analysis capabilities
5. Integrate with AI agents

**Deliverables:**
- Graph analytics library
- Pattern detection tools
- Agent integration
- Analysis examples

---

## Query Patterns

### 1. Find Direct Connections

```cypher
// Find all people directly connected to Jeffrey Epstein
MATCH (p1:Person {name: 'Jeffrey Epstein'})-[r]-(p2:Person)
RETURN p2.name, type(r), r.start_date, r.end_date
ORDER BY r.confidence DESC
LIMIT 50;
```

### 2. Find Shortest Path

```cypher
// Find shortest path between two people
MATCH path = shortestPath(
  (p1:Person {name: 'Jeffrey Epstein'})-[*..6]-(p2:Person {name: 'Bill Clinton'})
)
RETURN path;
```

### 3. Find Common Associates

```cypher
// Find people who know both Person A and Person B
MATCH (p1:Person {name: 'Jeffrey Epstein'})-[:KNOWS]-(common:Person)-[:KNOWS]-(p2:Person {name: 'Ghislaine Maxwell'})
WHERE p1 <> p2 AND p1 <> common AND p2 <> common
RETURN common.name, COUNT(*) as connection_strength
ORDER BY connection_strength DESC
LIMIT 20;
```

### 4. Travel Pattern Analysis

```cypher
// Find all co-travelers on specific flights
MATCH (p1:Person)-[t:TRAVELED_WITH]->(p2:Person)
WHERE t.date >= date('2005-01-01') AND t.date <= date('2010-12-31')
RETURN p1.name, p2.name, t.date, t.departure, t.destination, t.aircraft
ORDER BY t.date;
```

### 5. Temporal Relationship Query

```cypher
// Find relationships active during a specific time period
MATCH (p1:Person)-[r:KNOWS]-(p2:Person)
WHERE r.start_date <= date('2008-01-01')
  AND (r.end_date IS NULL OR r.end_date >= date('2008-12-31'))
RETURN p1.name, p2.name, r.relationship_type
ORDER BY r.confidence DESC;
```

### 6. Community Detection

```cypher
// Find densely connected communities
CALL gds.louvain.stream('person-network')
YIELD nodeId, communityId
WITH communityId, collect(gds.util.asNode(nodeId).name) AS members
WHERE size(members) > 3
RETURN communityId, members, size(members) as size
ORDER BY size DESC
LIMIT 10;
```

### 7. Centrality Analysis

```cypher
// Find most central/important people in network
CALL gds.pageRank.stream('person-network')
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS person, score
RETURN person.name, score
ORDER BY score DESC
LIMIT 20;
```

### 8. Evidence-Based Query

```cypher
// Find all evidence for a relationship
MATCH (p1:Person {name: 'Jeffrey Epstein'})-[r:KNOWS]-(p2:Person {name: 'Ghislaine Maxwell'})
WITH p1, p2, r
UNWIND r.source_docs AS doc_id
MATCH (d:Document {id: doc_id})
RETURN d.title, d.date, d.source, d.url
ORDER BY d.date;
```

### 9. Pattern Matching

```cypher
// Find triangular relationships (A knows B, B knows C, C knows A)
MATCH (a:Person)-[:KNOWS]-(b:Person)-[:KNOWS]-(c:Person)-[:KNOWS]-(a)
WHERE id(a) < id(b) AND id(b) < id(c)  // Avoid duplicates
RETURN a.name, b.name, c.name
LIMIT 50;
```

### 10. Missing Link Prediction

```cypher
// Find likely but undocumented relationships
// (People with many common associates but no direct link)
MATCH (p1:Person)-[:KNOWS]-(common:Person)-[:KNOWS]-(p2:Person)
WHERE p1 <> p2
  AND NOT (p1)-[:KNOWS]-(p2)
WITH p1, p2, COUNT(DISTINCT common) as common_count
WHERE common_count >= 3
RETURN p1.name, p2.name, common_count
ORDER BY common_count DESC
LIMIT 20;
```

---

## Integration

### Integration with PostgreSQL

**Strategy**: Maintain PostgreSQL as the source of truth, sync to Neo4j

```python
# Example ETL sync
def sync_entity_to_graph(entity_id: str):
    # 1. Fetch from PostgreSQL
    entity = fetch_entity_from_postgres(entity_id)
    
    # 2. Transform to graph node
    node_props = {
        'id': entity.id,
        'name': entity.name,
        'type': entity.entity_type,
        # ... other properties
    }
    
    # 3. Upsert to Neo4j
    with neo4j_driver.session() as session:
        session.run(
            """
            MERGE (p:Person {id: $id})
            SET p += $props
            SET p.updated_at = datetime()
            """,
            id=entity.id,
            props=node_props
        )
```

### Integration with AI Agents

```python
# Example agent tool for graph queries
class KnowledgeGraphTool:
    def find_connections(self, person1: str, person2: str) -> dict:
        """Find connections between two people"""
        query = """
        MATCH path = shortestPath(
          (p1:Person {name: $name1})-[*..6]-(p2:Person {name: $name2})
        )
        RETURN [node in nodes(path) | node.name] as path
        """
        
        with self.driver.session() as session:
            result = session.run(query, name1=person1, name2=person2)
            return result.single()['path']
```

### Integration with MCP Servers

Create a dedicated Knowledge Graph MCP Server:

```python
# mcp_servers/knowledge_graph/server.py
class KnowledgeGraphMCP:
    @mcp_tool
    async def query_graph(self, query: str, params: dict) -> dict:
        """Execute Cypher query on knowledge graph"""
        # ... implementation
    
    @mcp_tool
    async def find_entity(self, name: str, entity_type: str) -> dict:
        """Find entity by name"""
        # ... implementation
    
    @mcp_tool
    async def get_relationships(self, entity_id: str) -> list:
        """Get all relationships for an entity"""
        # ... implementation
```

---

## Best Practices

### 1. Data Quality

- **Validate before insert**: Check data quality before adding to graph
- **Confidence scores**: Always include confidence scores
- **Provenance**: Maintain links to source documents
- **Regular audits**: Periodically audit graph for inconsistencies

### 2. Performance

- **Use parameters**: Always use parameterized queries
- **Batch operations**: Batch inserts/updates for efficiency
- **Index strategically**: Create indexes for frequent queries
- **Monitor slow queries**: Track and optimize slow queries

### 3. Entity Resolution

- **Canonical names**: Maintain canonical name for each entity
- **Alias tracking**: Store all name variations as aliases
- **Manual review**: Have human review merge candidates
- **Reversible merges**: Keep history of merges

### 4. Temporal Data

- **ISO dates**: Use ISO 8601 format for dates
- **Handle uncertainty**: Support circa dates and ranges
- **Temporal validity**: Track when relationships were active
- **Timeline queries**: Design queries to filter by time

### 5. Documentation

- **Document schema**: Keep schema documentation current
- **Query examples**: Provide examples for common queries
- **ADRs**: Document significant decisions
- **Change log**: Track schema changes

---

## Appendix A: Neo4j Docker Setup

```yaml
# docker-compose.yml addition
services:
  neo4j:
    image: neo4j:5.15-community
    container_name: epstein_neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/your_password_here
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - ./neo4j/data:/data
      - ./neo4j/logs:/logs
      - ./neo4j/import:/var/lib/neo4j/import
    networks:
      - epstein_network
```

## Appendix B: Python Example Code

```python
# epstein/graph/client.py
from neo4j import GraphDatabase
from typing import List, Dict, Any

class EpsteinGraphClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def create_person(self, person_data: Dict[str, Any]) -> str:
        """Create or update a person node"""
        with self.driver.session() as session:
            result = session.run(
                """
                MERGE (p:Person {id: $id})
                SET p += $props
                SET p.updated_at = datetime()
                RETURN p.id
                """,
                id=person_data['id'],
                props=person_data
            )
            return result.single()['p.id']
    
    def find_connections(
        self,
        person1_id: str,
        person2_id: str,
        max_hops: int = 6
    ) -> List[List[str]]:
        """Find all paths between two people"""
        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH path = allShortestPaths(
                  (p1:Person {{id: $id1}})-[*..{max_hops}]-(p2:Person {{id: $id2}})
                )
                RETURN [node in nodes(path) | node.name] as names
                LIMIT 10
                """,
                id1=person1_id,
                id2=person2_id
            )
            return [record['names'] for record in result]
```

---

**End of Document**

For questions or contributions, see:
- Main documentation: `docs/`
- Discussion: GitHub Issues
- Contact: See `CONTRIBUTING.md`
