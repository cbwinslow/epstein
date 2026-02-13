# Recommendations

## 20260202_035430
- Add persistent download state checkpoints for resume across restarts.
- Consider storing batch manifests with archive hashes to verify integrity.
- Add CI job to run repair_project.py and surface report artifacts.
- Evaluate adding retry/backoff policies per-source to avoid aggressive retries.
