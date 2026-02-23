# n8n Workflows for Epstein Files Pipeline

This directory contains n8n workflow definitions for automating the Epstein Files pipeline.

## Workflows

### epstein-pipeline.json
Main pipeline workflow that automates:
1. **Schedule Trigger** - Runs hourly (configurable)
2. **Discover Collections** - Queries MCP server for available DOJ/FBI document collections
3. **Download Files** - Bulk downloads new documents
4. **Run OCR Pipeline** - Executes the Python pipeline for text extraction and embedding
5. **Verify Vectors** - Confirms vectors were stored in Qdrant
6. **Notify Complete** - Sends notification when done

## Setup

### Prerequisites
- n8n self-hosted or cloud instance
- Docker services running (see compose.yml):
  - MCP server (port 8765)
  - Qdrant (port 6333)
  - PostgreSQL (port 5432)

### Import Workflow
1. Open n8n interface
2. Go to Workflows → Import from File
3. Select `epstein-pipeline.json`
4. Configure credentials:
   - HTTP Basic Auth (if enabled on MCP server)
   - Email/Slack credentials for notifications
5. Activate workflow

### Manual Trigger
You can also add a Manual Trigger node alongside the Schedule Trigger for on-demand execution.

## Customization

### Adjust Schedule
Edit the "Schedule Trigger" node to change frequency:
- Hours, days, weeks intervals
- Cron expression support

### Add Custom Steps
Insert nodes between existing steps:
- Data validation
- Quality checks
- Additional notifications
- Error handling with retry

## Environment Variables

Configure in n8n or `.env`:
```
MCP_SERVER_URL=http://mcp-server:8765
QDRANT_URL=http://qdrant:6333
POSTGRES_DSN=postgresql://analysis:analysis@postgres:5432/analysis
```
