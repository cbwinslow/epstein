# Security Overview

## Principles
- Least privilege
- No secrets in repo
- Immutable source documents
- Full auditability

## Secrets
- Stored in environment variables
- Never committed
- Rotatable

## Database
- Separate ingestion role
- Read-only analysis role
- Encrypted connections when remote

## Files
- Hash verification
- No overwrites

See `docs/SECURITY_SCANNER.md` for pre-commit scanner diagnostics and fallback instructions.
