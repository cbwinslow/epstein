# Cloudflare Deployment for MCP Servers

This guide describes deploying the MCP servers to Cloudflare-compatible infrastructure.

## Option A: Cloudflare Tunnel (fastest)

Use `cloudflared` to expose a locally running MCP server:

```bash
cloudflared tunnel --url http://localhost:8780
```

Pros: minimal changes, no container build required.

## Option B: Cloudflare Containers (recommended for hosted services)

1. Build a container image that runs the MCP server:

```bash
docker build -t epstein-files-processor -f mcp_servers/epstein_files_processor/Dockerfile .
```

2. Push the image to your registry.
3. Deploy it to Cloudflare Containers and set the service port to `8780`.

## MCP endpoint checklist

- `POST /process/run`
- `GET /process/status/{task_id}`
- `GET /process/status`

## Notes

- Cloudflare Workers are not a great fit for long-lived pipeline runs. Prefer containers or tunnels for long-running OCR/NER workloads.
- Configure `EPSTEIN_DSN` and `QDRANT_URL` as environment variables if using embeddings and ingestion.
