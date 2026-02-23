# Epstein Files AI Analysis Architecture

## Executive Summary

This document outlines the architecture for AI-powered document analysis using free/open-source tools.

## Recommended Tech Stack

### 1. AI Models (Free Options)

| Option | Cost | Pros | Cons |
|--------|------|------|------|
| **Ollama** | Free | Runs locally, privacy, no API costs | Requires local compute |
| **OpenRouter** | Free tier | Easy API, multiple models | Rate limits |
| **Cloudflare Workers** | Free tier | Fast, edge computing | Limited context |

**Recommendation:** Use Ollama as primary (local, free, private), OpenRouter as fallback.

### 2. RAG Database

- **Qdrant** (already in project) - Primary vector DB
- **Chroma** - Alternative/local option
- **PostgreSQL + pgvector** - Already available

### 3. Agent Orchestration

**Option A: Custom Agent System (Recommended)**
- Build on existing `base_agent.py`
- Add task queue with SQLite/Redis
- Implement supervisor pattern

**Option B: Use n8n**
- Already has workflow orchestration
- Good for automation
- Less flexible for complex reasoning

**Option C: AutoGen (Microsoft)**
- Good for multi-agent
- Requires Azure/OpenAI

### 4. Long-Running Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Super Agent (Supervisor)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │  Task Queue │  │   Memory   │  │   Model Interface   ││
│  │  (SQLite)   │  │   (Redis)  │  │  (Ollama/OpenRouter)││
│  └─────────────┘  └─────────────┘  └─────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Document      │   │ Entity       │   │ Analysis     │
│ Processor     │   │ Extractor    │   │ Agent        │
│ Agent         │   │ Agent        │   │ Agent        │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Qdrant RAG    │
                    │  + PostgreSQL  │
                    └─────────────────┘
```

## Analysis Capabilities

### Document Types to Analyze
1. **Flight Logs** → Extract: aircraft, routes, passengers, dates
2. **Emails** → Extract: sender, recipient, date, subject, entities
3. **Meetings** → Extract: attendees, location, date, topic
4. **Financial** → Extract: amounts, parties, dates
5. **Phone Records** → Extract: caller, callee, duration, date

### Entity Types
- PERSON (people names)
- ORG (organizations)
- GPE (locations)
- DATE/TIME
- FLIGHT (aircraft, routes)
- MONEY
- CONTACT (phone, email)

### Relationship Types
- COMMUNICATED_WITH
- FLIGHT_WITH
- MET_AT
- PAID
- WORKED_FOR
- ASSOCIATED_WITH

## Implementation Plan

### Phase 1: RAG Setup
1. Connect Qdrant to document pipeline
2. Create embeddings for all documents
3. Set up semantic search

### Phase 2: Agent System
1. Create Supervisor Agent with task queue
2. Build specialized sub-agents
3. Implement message passing

### Phase 3: Analysis
1. Entity extraction pipeline
2. Relationship mapping
3. Timeline construction

### Phase 4: Automation
1. n8n workflow integration
2. Scheduled analysis runs
3. Reporting

## API Keys Required (Free Tier)

```
OPENROUTER_API_KEY=<free key from openrouter.ai>
OLLAMA_HOST=http://localhost:11434
QDRANT_URL=http://localhost:6333
POSTGRES_DSN=postgresql://...
```

## Usage

```bash
# Start Ollama (local AI)
ollama serve
ollama pull mistral

# Run analysis
python -m agents.supervisor analyze --query "Who did Epstein meet in 2001?"

# Or use n8n workflow
n8n execute --workflow epstein-analysis.json
```
