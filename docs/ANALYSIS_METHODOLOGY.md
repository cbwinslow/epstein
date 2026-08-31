# Analysis Methodology & Playbook

**Version**: 1.0
**Date**: 2025-12-31
**Purpose**: Guide for conducting evidence-based analysis of Epstein documents

## Table of Contents

1. [Core Principles](#core-principles)
2. [Analysis Workflow](#analysis-workflow)
3. [Query Patterns](#query-patterns)
4. [Finding Documentation](#finding-documentation)
5. [Quality Standards](#quality-standards)
6. [Common Pitfalls](#common-pitfalls)

---

## Core Principles

### 1. Evidence-Based Analysis

**Every claim must be supported by documentary evidence.**

- Link findings to specific documents
- Include page numbers and excerpts
- Provide source URLs where available
- Use document IDs for traceability

### 2. Provenance Required

**Maintain complete audit trail from finding to source.**

- Document discovery methodology
- Track all steps in analysis
- Enable reproduction of findings
- Support verification by others

### 3. Confidence Scoring

**Assess and communicate certainty levels.**

- **High Confidence**: Multiple independent sources corroborate
- **Medium Confidence**: Single reliable source or multiple indirect sources
- **Low Confidence**: Limited evidence, requires verification
- **Speculative**: Inference or hypothesis requiring investigation

### 4. Avoid Premature Conclusions

**Focus on relationships, not narratives.**

- Document what is observed, not what it "means"
- Distinguish between evidence and interpretation
- Present multiple interpretations where applicable
- Flag speculation clearly

### 5. Cross-Reference Everything

**Validate claims across multiple sources.**

- Never rely on single source
- Seek corroborating evidence
- Identify and document contradictions
- Note information gaps

---

## Analysis Workflow

### Phase 1: Question Formation

**Start with a specific, answerable question.**

Examples of good questions:
- ✅ "Who traveled with Jeffrey Epstein to Little St. James in 2005-2006?"
- ✅ "What are the documented connections between Person A and Person B?"
- ✅ "What meetings included both Epstein and Person X?"

Examples of poor questions:
- ❌ "What was Epstein really doing?" (too broad, subjective)
- ❌ "Who is guilty?" (legal conclusion, not analysis)
- ❌ "What's the conspiracy?" (assumes conclusion)

### Phase 2: Source Identification

**Identify relevant documents.**

Methods:
1. **Keyword Search**: Use vector search for semantic queries
2. **Entity Search**: Find documents mentioning specific entities
3. **Date Range**: Filter by temporal criteria
4. **Document Type**: Focus on specific document types (flight logs, emails, etc.)

```python
# Example: Find documents about flights in 2005
query = """
SELECT DISTINCT d.id, d.title, d.source_url
FROM doc_analysis.documents d
JOIN doc_analysis.document_text dt ON d.id = dt.document_id
WHERE dt.extracted_text ILIKE '%flight%'
  AND d.date >= '2005-01-01'
  AND d.date <= '2005-12-31'
ORDER BY d.date;
```

### Phase 3: Data Extraction

**Extract relevant information systematically.**

For each source document:
1. Record document ID, title, date, source
2. Note relevant page numbers
3. Extract verbatim quotes or paraphrase accurately
4. Identify all entities mentioned
5. Note temporal information (dates, durations)
6. Record contextual information

Use structured extraction:
```python
finding = {
    "document_id": "DOJ_DS01_F123",
    "page": 45,
    "excerpt": "Flight manifest dated January 15, 2010...",
    "entities": ["Jeffrey Epstein", "John Doe", "N-Number"],
    "date": "2010-01-15",
    "location": "Little St. James",
    "evidence_type": "flight_log"
}
```

### Phase 4: Cross-Reference

**Validate against other sources.**

1. Search for same event in other documents
2. Look for corroborating evidence
3. Identify contradictions
4. Check timeline consistency
5. Verify entity spellings and aliases

```python
# Example: Cross-reference flight
# Find other documents mentioning same date and entities
cross_refs = graph.query("""
MATCH (p1:Person {name: 'Jeffrey Epstein'})-[r]->(e:Event {date: '2010-01-15'})
MATCH (e)-[:MENTIONED_IN]->(d:Document)
RETURN d.title, d.source, r
""")
```

### Phase 5: Synthesis

**Combine evidence into coherent finding.**

1. Summarize what evidence shows
2. Calculate confidence level
3. Note any contradictions or gaps
4. Identify next steps for investigation
5. Connect to related findings

### Phase 6: Documentation

**Create formal finding record.**

Use Finding Issue Template:
- Assign Finding ID (F-YYYY-NNN)
- Categorize finding
- Document all evidence with citations
- List entities and timeline
- Provide analysis and interpretation
- Record verification status
- Suggest next steps

### Phase 7: Review

**Quality assurance check.**

- Verify all sources are cited correctly
- Check for logical consistency
- Ensure no speculation without labeling
- Confirm finding meets quality standards
- Get peer review if possible

---

## Query Patterns

### Pattern 1: Entity Profile

**Goal**: Build comprehensive profile of an entity.

**Queries**:
```cypher
// 1. Find entity and basic info
MATCH (p:Person {name: 'Jeffrey Epstein'})
RETURN p

// 2. Find all direct relationships
MATCH (p:Person {name: 'Jeffrey Epstein'})-[r]-(other)
RETURN type(r), other, r
ORDER BY r.confidence DESC

// 3. Find all documents mentioning entity
MATCH (p:Person {name: 'Jeffrey Epstein'})-[:MENTIONED_IN]->(d:Document)
RETURN d.title, d.date, d.source_url
ORDER BY d.date
```

**Analysis Steps**:
1. Extract all relationship types
2. Categorize by: personal, business, travel, communication
3. Build timeline of relationships
4. Identify key associates
5. Note changes over time

### Pattern 2: Relationship Analysis

**Goal**: Investigate connection between two entities.

**Queries**:
```cypher
// 1. Direct relationships
MATCH (p1:Person {name: 'Person A'})-[r]-(p2:Person {name: 'Person B'})
RETURN r, r.start_date, r.end_date, r.source_docs

// 2. Indirect connections (paths)
MATCH path = shortestPath(
  (p1:Person {name: 'Person A'})-[*..4]-(p2:Person {name: 'Person B'})
)
RETURN [node in nodes(path) | node.name] as path

// 3. Common associates
MATCH (p1:Person {name: 'Person A'})-[:KNOWS]-(common)-[:KNOWS]-(p2:Person {name: 'Person B'})
RETURN common.name, COUNT(*) as strength
ORDER BY strength DESC
```

**Analysis Steps**:
1. Document direct relationships with evidence
2. Map indirect connections
3. Find patterns in connections (e.g., frequent intermediaries)
4. Note temporal aspects (when active)
5. Assess relationship strength

### Pattern 3: Timeline Reconstruction

**Goal**: Build chronology of events involving entities.

**Queries**:
```sql
-- SQL: Get all dated events for entity
SELECT
  e.entity_text as entity,
  dt.page_number,
  d.date as doc_date,
  d.title,
  d.source_url,
  substring(dt.extracted_text from position(e.entity_text in dt.extracted_text) - 100 for 300) as context
FROM doc_analysis.entities e
JOIN doc_analysis.document_text dt ON e.extracted_text_id = dt.id
JOIN doc_analysis.documents d ON dt.document_id = d.id
WHERE e.entity_text = 'Jeffrey Epstein'
  AND d.date IS NOT NULL
ORDER BY d.date, dt.page_number;
```

```cypher
// Cypher: Get timeline from graph
MATCH (p:Person {name: 'Jeffrey Epstein'})-[r]->(e:Event)
RETURN e.date, e.type, e.description, r
ORDER BY e.date
```

**Analysis Steps**:
1. Extract all dated events
2. Normalize dates to ISO format
3. Sort chronologically
4. Identify patterns or clusters
5. Note timeline gaps
6. Cross-reference events

### Pattern 4: Travel Pattern Analysis

**Goal**: Analyze travel patterns from flight logs.

**Queries**:
```cypher
// Find all flights for person
MATCH (p:Person {name: 'Jeffrey Epstein'})-[t:TRAVELED_WITH]->(other:Person)
WHERE t.date IS NOT NULL
RETURN t.date, t.aircraft, t.departure, t.destination,
       collect(other.name) as passengers
ORDER BY t.date

// Find frequent travel companions
MATCH (p:Person {name: 'Jeffrey Epstein'})-[t:TRAVELED_WITH]->(other:Person)
RETURN other.name, COUNT(t) as flight_count
ORDER BY flight_count DESC
LIMIT 20

// Find frequent routes
MATCH (p:Person {name: 'Jeffrey Epstein'})-[t:TRAVELED_WITH]->()
RETURN t.departure, t.destination, COUNT(*) as frequency
ORDER BY frequency DESC
```

**Analysis Steps**:
1. Map all documented flights
2. Identify frequent routes
3. Find regular travel companions
4. Note temporal patterns (seasonal, etc.)
5. Cross-reference with events at destinations
6. Identify anomalous trips

### Pattern 5: Communication Network

**Goal**: Analyze communication patterns.

**Queries**:
```cypher
// Find communication partners
MATCH (p:Person {name: 'Jeffrey Epstein'})-[c:COMMUNICATED_WITH]->(other)
RETURN other.name, c.medium, c.frequency, c.message_count
ORDER BY c.message_count DESC

// Find communication clusters
MATCH (p:Person)-[c:COMMUNICATED_WITH]-(other:Person)
WHERE p.name IN ['Person A', 'Person B', 'Person C']
RETURN p.name, other.name, c
```

**Analysis Steps**:
1. Identify primary communication partners
2. Categorize by medium (email, phone, in-person)
3. Analyze frequency and volume
4. Track changes over time
5. Identify communication hubs
6. Find isolated groups

### Pattern 6: Fact Verification

**Goal**: Verify or refute a specific claim.

**Workflow**:
1. Identify the claim to verify
2. Search for direct evidence
3. Search for indirect/corroborating evidence
4. Search for contradicting evidence
5. Assess overall evidence weight
6. Document verification conclusion

**Example**:
```
Claim: "Person A met Person B on January 15, 2010"

Evidence FOR:
- Document 1: Email dated Jan 15, 2010 mentions "meeting today"
- Document 2: Calendar entry shows meeting
- Document 3: Meeting notes from that date

Evidence AGAINST:
- Document 4: Person A's travel records show they were elsewhere

Conclusion: CONTRADICTED - Evidence suggests Person A was not present
Confidence: HIGH (multiple sources for both sides)
```

---

## Finding Documentation

### Finding Structure

Every finding should include:

1. **Finding ID**: Unique identifier (F-YYYY-NNN)
2. **Category**: Entity Relationship, Timeline, Communication, etc.
3. **Confidence**: High, Medium, Low
4. **Summary**: 2-3 sentence overview
5. **Detailed Description**: Complete narrative
6. **Evidence List**: All supporting sources
7. **Entities**: All entities involved
8. **Timeline**: Relevant dates
9. **Cross-References**: Related findings
10. **Analysis**: Interpretation and significance
11. **Verification Status**: Unverified, Verified, Disputed
12. **Methodology**: How discovered
13. **Next Steps**: Recommended actions

### Evidence Citation Format

```
Document: [Document Title or ID]
Source: [Source URL or Repository]
Date: [Document Date]
Page: [Page Number(s)]
Excerpt: "[Verbatim quote or paraphrase]"
Chunk ID: [chunk_id if applicable]
Retrieved: [Date accessed]
```

### Example Finding

```markdown
# Finding F-2025-001: Documented Travel Connection

**Category**: Travel Pattern
**Confidence**: High
**Date Created**: 2025-12-31

## Summary
Flight logs show Person A traveled with Jeffrey Epstein on three documented occasions
between 2005-2007, visiting Little St. James island twice and Palm Beach once.

## Evidence

1. Document: FBI_Vault_Flight_Logs_2005.pdf
   Source: https://vault.fbi.gov/jeffrey-epstein/...
   Date: 2005-06-15
   Page: 23
   Excerpt: "Passenger manifest: Jeffrey Epstein, Person A, [pilots]"
   Departure: Teterboro, NJ
   Destination: Little St. James, USVI
   Aircraft: N-[tail number]

2. Document: FBI_Vault_Flight_Logs_2006.pdf
   Source: https://vault.fbi.gov/jeffrey-epstein/...
   Date: 2006-08-20
   Page: 45
   Excerpt: "Flight log shows Person A as passenger..."
   [additional details]

3. Document: Flight_Records_2007_Q1.pdf
   [additional evidence]

## Analysis
Three documented flights over a 2-year period suggest an established relationship.
The destinations (private island, private residence) indicate personal rather than
business travel. Cross-reference with meeting records shows...

## Next Steps
- Search for other documents from same time period mentioning Person A
- Investigate business relationships between Person A and Epstein
- Check for contemporaneous news articles or events
```

---

## Quality Standards

### Mandatory Requirements

✅ **Must Have**:
- Document IDs for all sources
- Page numbers where applicable
- Confidence level assessment
- At least 2 sources for HIGH confidence claims
- Clear distinction between evidence and interpretation
- Verification status
- Cross-references checked

❌ **Must Not Have**:
- Speculation presented as fact
- Unsourced claims
- Conclusions without evidence
- Missing provenance information
- Ambiguous confidence levels

### Quality Checklist

Before submitting a finding:

- [ ] All evidence includes document IDs
- [ ] Page numbers provided where applicable
- [ ] Source URLs included when available
- [ ] Entities clearly identified and disambiguated
- [ ] Dates in ISO format (YYYY-MM-DD)
- [ ] Confidence level justified
- [ ] Cross-references checked
- [ ] No speculation without clear labeling
- [ ] Methodology documented
- [ ] Peer review completed (if possible)

---

## Common Pitfalls

### Pitfall 1: Cherry-Picking Evidence

**Problem**: Only presenting evidence that supports desired conclusion.

**Solution**: Actively search for contradicting evidence. Document all relevant evidence, including contradictions.

### Pitfall 2: Confirmation Bias

**Problem**: Interpreting ambiguous evidence to fit preconceived narrative.

**Solution**: Consider alternative interpretations. Have others review findings.

### Pitfall 3: Single-Source Reliance

**Problem**: Basing findings on uncorroborated single source.

**Solution**: Always seek multiple sources. Label single-source findings as LOW confidence.

### Pitfall 4: Temporal Inconsistencies

**Problem**: Claiming relationships or events without considering timing.

**Solution**: Always check dates. Verify entities could have been in same place at same time.

### Pitfall 5: Entity Misidentification

**Problem**: Confusing similarly-named entities.

**Solution**: Use entity disambiguation. Include identifying details (DOB, location, etc.).

### Pitfall 6: Missing Context

**Problem**: Excerpting text without crucial context.

**Solution**: Include surrounding text. Provide document-level context.

### Pitfall 7: Speculation as Fact

**Problem**: Presenting inference or hypothesis as established fact.

**Solution**: Clearly label speculation. Use conditional language ("may indicate", "suggests", "possible that").

### Pitfall 8: Privacy Violations

**Problem**: Including unnecessary personal information.

**Solution**: Redact unnecessary personal details. Focus on relevant facts only.

---

## Analysis Examples

### Example 1: Good Analysis

**Finding**: Multiple sources document meetings between Person A and Jeffrey Epstein during 2005-2006 period.

**Evidence**:
1. Email dated 2005-03-15 from Person A to assistant: "Meeting with JE tomorrow at 2pm"
2. Calendar entry for 2005-03-16 shows "JE - 2pm"
3. Flight log shows Person A traveled on Epstein aircraft on 2005-03-16
4. Testimony from Person B mentions seeing Person A at Epstein residence in "Spring 2005"

**Confidence**: HIGH (multiple independent sources corroborate)

**Analysis**: Four independent sources corroborate meetings during this period. Email and calendar provide documentary evidence. Flight log confirms travel. Testimony provides third-party verification. Timeline consistency across sources increases confidence.

**What Makes This Good**:
✅ Multiple sources
✅ Different source types
✅ Specific dates
✅ Corroborating details
✅ Clear confidence justification

### Example 2: Poor Analysis (AVOID)

**Finding**: Person A was involved in Epstein's criminal activities.

**Evidence**:
1. Person A met with Epstein several times.
2. Person A traveled on Epstein's plane.

**Problems**:
❌ Legal conclusion without basis
❌ Vague ("several times" - how many? when?)
❌ Insufficient evidence for claim
❌ No specific document citations
❌ No page numbers
❌ Speculation presented as fact

**How to Fix**: Focus on documented facts, not conclusions. Provide specific dates, document IDs, and citations. State only what evidence shows, not what it "means."

---

## Tools and Resources

### Database Queries

**PostgreSQL Connection**:
```python
import psycopg
conn = psycopg.connect(os.getenv('EPSTEIN_DSN'))
```

**Neo4j Connection**:
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver(uri, auth=(user, password))
```

**Vector Search**:
```python
from qdrant_client import QdrantClient
client = QdrantClient(url=os.getenv('QDRANT_URL'))
```

### Analysis Scripts

Available in `epstein/analysis/`:
- `entity_profile.py`: Generate entity profiles
- `relationship_finder.py`: Find connections between entities
- `timeline_builder.py`: Build chronological timelines
- `flight_analyzer.py`: Analyze flight patterns
- `verification_checker.py`: Cross-reference verification

### Agents

AI Agents for analysis:
- **Entity Analysis Agent**: Build entity profiles
- **Relationship Discovery Agent**: Find connections
- **Timeline Agent**: Reconstruct chronologies
- **Verification Agent**: Fact-check claims

---

## Appendix: Query Cheatsheet

### PostgreSQL Queries

```sql
-- Find all entities of type PERSON
SELECT DISTINCT entity_text
FROM doc_analysis.entities
WHERE entity_type = 'PERSON'
ORDER BY entity_text;

-- Find documents mentioning specific entity
SELECT d.id, d.title, d.date, dt.page_number
FROM doc_analysis.documents d
JOIN doc_analysis.document_text dt ON d.id = dt.document_id
JOIN doc_analysis.entities e ON e.extracted_text_id = dt.id
WHERE e.entity_text = 'Jeffrey Epstein'
ORDER BY d.date, dt.page_number;

-- Find entity co-occurrences
SELECT e1.entity_text as entity1, e2.entity_text as entity2,
       COUNT(DISTINCT e1.document_id) as doc_count
FROM doc_analysis.entities e1
JOIN doc_analysis.entities e2 ON e1.document_id = e2.document_id
WHERE e1.entity_text < e2.entity_text  -- Avoid duplicates
  AND e1.entity_type = 'PERSON'
  AND e2.entity_type = 'PERSON'
GROUP BY e1.entity_text, e2.entity_text
HAVING COUNT(DISTINCT e1.document_id) >= 3
ORDER BY doc_count DESC;
```

### Neo4j Queries (Cypher)

```cypher
// Find entity
MATCH (p:Person {name: 'Jeffrey Epstein'})
RETURN p

// Find relationships
MATCH (p:Person {name: 'Jeffrey Epstein'})-[r]->(other)
RETURN type(r), other, r
ORDER BY r.confidence DESC

// Find paths
MATCH path = shortestPath(
  (p1:Person)-[*..6]-(p2:Person)
)
WHERE p1.name = 'Person A' AND p2.name = 'Person B'
RETURN path

// Find common associates
MATCH (p1:Person)-[:KNOWS]-(common)-[:KNOWS]-(p2:Person)
WHERE p1.name = 'Person A' AND p2.name = 'Person B'
RETURN common.name
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-31
**Maintained By**: Epstein Project Analysis Team
**Feedback**: Submit issues via GitHub Issue Template
