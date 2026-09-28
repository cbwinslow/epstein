# ADR 001: Graph Database Selection for Knowledge Graph

**Date**: 2025-12-31
**Status**: Proposed
**Deciders**: Technical Team
**Context**: Knowledge Graph Implementation (Phase 3)

## Context and Problem Statement

The Epstein document analysis project requires a graph database to represent and query complex relationships between entities (people, organizations, locations, events) extracted from documents. We need to select a graph database technology that balances capability, performance, ease of use, and integration with our existing stack.

## Decision Drivers

1. **Query Performance**: Must handle complex graph traversals efficiently
2. **Scalability**: Must support 10,000+ nodes and 50,000+ relationships
3. **Query Language**: Need expressive, intuitive query language
4. **Python Integration**: Excellent Python driver support required
5. **Visualization**: Good tools for graph visualization and exploration
6. **Community & Support**: Active community and good documentation
7. **Deployment**: Easy to deploy with Docker
8. **Cost**: Prefer open source solutions
9. **Learning Curve**: Reasonable onboarding time for team
10. **PostgreSQL Integration**: Should integrate well with existing PostgreSQL data

## Considered Options

1. **Neo4j Community Edition**
2. **Apache AGE (A Graph Extension for PostgreSQL)**
3. **RedisGraph**

## Decision Outcome

**Chosen option**: Neo4j Community Edition

### Rationale

Neo4j Community Edition is selected as the graph database for the following reasons:

#### Strengths

1. **Industry Leader**: Neo4j is the most mature and widely-adopted graph database
   - Proven at scale in production environments
   - Used by major enterprises for similar use cases
   - Extensive real-world validation

2. **Query Language**: Cypher is powerful, intuitive, and well-documented
   - Declarative pattern-matching syntax
   - Easy to express complex graph queries
   - Large knowledge base and community examples

3. **Tooling**: Best-in-class development and visualization tools
   - Neo4j Browser for interactive exploration
   - Neo4j Bloom for visual analytics
   - Comprehensive monitoring and profiling tools

4. **Python Support**: Official `neo4j` Python driver is excellent
   - Well-maintained and documented
   - Support for async operations
   - Connection pooling and performance optimization

5. **Graph Algorithms**: Built-in Graph Data Science library
   - Community detection (Louvain, Label Propagation)
   - Centrality algorithms (PageRank, Betweenness)
   - Path finding and similarity algorithms
   - Pre-implemented and optimized

6. **Community & Resources**: Large, active community
   - Extensive documentation and tutorials
   - Active Stack Overflow community
   - Regular updates and improvements

7. **Performance**: Optimized for graph traversals
   - Native graph storage and processing
   - Efficient index structures
   - Query optimizer for complex patterns

#### Trade-offs Accepted

1. **Separate Database**: Neo4j runs separately from PostgreSQL
   - **Pro**: Optimized specifically for graph operations
   - **Con**: Data duplication between PostgreSQL and Neo4j
   - **Mitigation**: PostgreSQL remains source of truth, Neo4j is computed view

2. **Resource Requirements**: Neo4j can be memory-intensive
   - **Pro**: In-memory operations provide excellent performance
   - **Con**: Requires adequate memory allocation (2GB+ recommended)
   - **Mitigation**: Allocate appropriate resources in Docker deployment

3. **Community Edition Limitations**: Some enterprise features not available
   - **Pro**: Free and open source
   - **Con**: Lacks clustering, hot backups, advanced security
   - **Mitigation**: Community edition sufficient for our use case

### Alternative: Apache AGE

Apache AGE was seriously considered for its PostgreSQL integration.

**Pros:**
- Runs as PostgreSQL extension
- No separate database needed
- Can query relational and graph data together
- Familiar PostgreSQL tooling

**Cons:**
- Relatively new project (less mature)
- Smaller community and fewer resources
- Limited visualization options
- Less battle-tested at scale

**Why not chosen**: While AGE's PostgreSQL integration is attractive, Neo4j's maturity, tooling, and community support provide better risk mitigation for a critical component.

### Alternative: RedisGraph

RedisGraph was considered for its performance characteristics.

**Pros:**
- Very fast query performance
- Lightweight deployment
- Simple integration

**Cons:**
- In-memory only (size limitations)
- Smaller community than Neo4j
- Less sophisticated than Neo4j
- Fewer built-in algorithms

**Why not chosen**: In-memory limitation and smaller ecosystem made it less suitable for our requirements.

## Architecture Integration

### Data Flow

```
PostgreSQL (Source of Truth)
    ↓
ETL Pipeline (Python)
    ↓
Neo4j (Graph View)
    ↓
Query APIs & Agents
    ↓
Analysis & Visualization
```

### Synchronization Strategy

1. **Initial Load**: Bulk import from PostgreSQL to Neo4j
2. **Incremental Updates**: Periodic sync of new/changed entities
3. **Event-Driven**: Option to sync on document ingestion events
4. **Idempotency**: All sync operations idempotent

### Docker Deployment

```yaml
services:
  neo4j:
    image: neo4j:5.15-community
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
    volumes:
      - ./neo4j/data:/data
```

## Consequences

### Positive

1. **Powerful Queries**: Cypher enables sophisticated relationship queries
2. **Visualization**: Excellent tools for graph exploration
3. **Community**: Large community provides support and examples
4. **Algorithms**: Built-in graph algorithms save development time
5. **Performance**: Optimized for graph operations
6. **Documentation**: Extensive documentation and learning resources

### Negative

1. **Complexity**: Additional database to maintain and monitor
2. **Sync Overhead**: Need to sync data from PostgreSQL
3. **Learning Curve**: Team needs to learn Cypher
4. **Resources**: Requires memory allocation and monitoring

### Neutral

1. **Vendor**: Neo4j Inc. maintains the project (hybrid open source/commercial model)
2. **License**: GPL v3 for Community Edition (Apache 2.0 for drivers)

## Implementation Plan

### Phase 1: Setup (Week 1)
- Deploy Neo4j in Docker Compose
- Install Python neo4j driver
- Create basic connection utilities
- Set up monitoring

### Phase 2: Schema (Week 1-2)
- Define node and edge types
- Create constraints and indexes
- Document schema
- Write schema tests

### Phase 3: ETL (Week 2-4)
- Build PostgreSQL to Neo4j ETL
- Implement entity sync
- Implement relationship sync
- Add error handling and logging

### Phase 4: Queries (Week 5-6)
- Implement core query patterns
- Build query library
- Create query API
- Performance optimization

### Phase 5: Integration (Week 7-8)
- Integrate with AI agents
- Create MCP server
- Build visualization
- Documentation

## Validation

This decision will be validated by:

1. **Performance Benchmarks**: Query response times <2 seconds
2. **Scale Testing**: Successfully handling 10K+ entities
3. **Query Complexity**: Able to express required analysis queries
4. **Team Feedback**: Team comfortable with Cypher after 2 weeks
5. **Integration Success**: Successful integration with agents and APIs

## References

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Apache AGE Documentation](https://age.apache.org/)
- [Graph Database Comparison](https://db-engines.com/en/system/Neo4j%3BApache+AGE)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)

## Related Decisions

- ADR 002: Graph Schema Design (To be written)
- ADR 003: Entity Resolution Strategy (To be written)

## Changelog

- 2025-12-31: Initial draft
- TBD: Decision approval
- TBD: Implementation start

---

**Note**: This ADR is in "Proposed" status and subject to review and approval.
