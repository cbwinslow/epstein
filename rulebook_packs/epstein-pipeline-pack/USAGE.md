# Using this pack with rulebook-ai

rulebook-ai supports adding packs from GitHub (`github:`) or local directories (`local:`).

## Add this pack to a project (local development)
From your Epstein pipeline repository root:

```bash
uvx rulebook-ai packs add local:./rulebook_packs/epstein-pipeline-pack
uvx rulebook-ai project sync --all
```

Tip: Commit your `memory/` and `tools/` folders, but ignore generated artifacts like `.rulebook-ai/` and assistant-specific rule outputs.
