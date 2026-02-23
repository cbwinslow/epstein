# API Keys and Secrets Management Guide

This guide documents how to configure API keys and secrets for the Epstein project.

## Overview

The Epstein project integrates with several external services that require API keys:

- **OpenRouter** - For accessing free LLM models
- **GitHub** - For repository access and CI/CD
- **DOJ/FBI APIs** - For downloading official documents (no key typically required)
- **Qdrant** - Vector database (optional authentication)
- **PostgreSQL** - Relational database (credentials required)
- **OpenTelemetry** - Observability (optional)

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your API keys:**
   ```bash
   nano .env  # or your preferred editor
   ```

3. **Never commit `.env` to git:**
   ```bash
   # Already in .gitignore, but verify:
   git check-ignore .env
   ```

## Configuration Methods

The project supports multiple methods for managing secrets, listed by priority:

### Method 1: Environment Variables (Recommended for Development)

Create a `.env` file in the project root:

```bash
# OpenRouter API (for free LLM models)
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# GitHub (for CI/CD and automation)
GITHUB_TOKEN=your_github_token_here

# Database Credentials
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=analysis
POSTGRES_USER=analysis
POSTGRES_PASSWORD=your_secure_password

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # Optional, leave empty for local development

# OpenTelemetry (optional)
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
OTEL_SERVICE_NAME=epstein

# Cloudflare R2 (optional, for artifact storage)
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket_name
```

**Load environment variables:**

The project automatically loads `.env` files using `python-dotenv`.

### Method 2: dotenvx (Encrypted Secrets - Recommended for Production)

[dotenvx](https://dotenvx.com/) provides encrypted environment variable management.

**Installation:**
```bash
# Install dotenvx
npm install -g @dotenvx/dotenvx
# or
curl -sfS https://dotenvx.sh/install.sh | sh
```

**Setup:**
```bash
# Create encrypted .env.keys file
dotenvx set OPENROUTER_API_KEY "your_key"

# Generate .env.vault for deployment
dotenvx encrypt
```

**Usage:**
```bash
# Run commands with encrypted env
dotenvx run -- python scripts/your_script.py

# Or in Python scripts:
import dotenvx
dotenvx.load()
```

**Documentation:**
- [dotenvx Documentation](https://dotenvx.com/docs)
- [Encryption Guide](https://dotenvx.com/docs/encryption)

### Method 3: GitHub Repository Secrets

For CI/CD workflows and GitHub Actions.

**Setup via GitHub UI:**

1. Go to your repository on GitHub
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret:
   - `OPENROUTER_API_KEY`
   - `POSTGRES_PASSWORD`
   - `CLOUDFLARE_R2_SECRET_ACCESS_KEY`
   - etc.

**Setup via GitHub CLI:**

```bash
# Install GitHub CLI
# https://cli.github.com/

# Login
gh auth login

# Add secrets
gh secret set OPENROUTER_API_KEY --body "your_key"
gh secret set POSTGRES_PASSWORD --body "your_password"

# List secrets
gh secret list
```

**Usage in GitHub Actions:**

```yaml
# .github/workflows/your-workflow.yml
jobs:
  your-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Your step
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: |
          python scripts/your_script.py
```

### Method 4: Cloudflare Secrets (for Workers/Pages)

For deployments on Cloudflare infrastructure.

**Using Wrangler CLI:**

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Add secrets
wrangler secret put OPENROUTER_API_KEY
wrangler secret put POSTGRES_PASSWORD

# List secrets
wrangler secret list
```

**Using Cloudflare Dashboard:**

1. Go to Cloudflare Dashboard
2. Workers & Pages → Your Worker/Page
3. Settings → Variables and Secrets
4. Add your secrets

**Documentation:**
- [Cloudflare Secrets Documentation](https://developers.cloudflare.com/workers/configuration/secrets/)

### Method 5: Bitwarden CLI (for Team Management)

[Bitwarden](https://bitwarden.com/) provides secure password/secret management with CLI access.

**Installation:**

```bash
# Install Bitwarden CLI
npm install -g @bitwarden/cli

# Or download from https://bitwarden.com/download/
```

**Setup:**

```bash
# Login
bw login

# Unlock vault
bw unlock
# Save session key: export BW_SESSION="your_session_key"

# Create a secure note or item for the project
bw create item --name "Epstein Project Keys" --type 2
```

**Retrieve Secrets:**

```bash
# Get a specific secret
bw get item "Epstein Project Keys" | jq -r '.notes'

# Export all secrets as JSON
bw get item "Epstein Project Keys" --session $BW_SESSION
```

**Integration Script:**

Create `scripts/load_secrets_from_bitwarden.sh`:

```bash
#!/bin/bash
# Load secrets from Bitwarden into environment

if [ -z "$BW_SESSION" ]; then
    echo "Error: BW_SESSION not set. Run: export BW_SESSION=\"\$(bw unlock --raw)\""
    exit 1
fi

# Get secrets from Bitwarden
SECRETS=$(bw get item "Epstein Project Keys" --session $BW_SESSION | jq -r '.notes')

# Parse and export
export OPENROUTER_API_KEY=$(echo "$SECRETS" | grep OPENROUTER_API_KEY | cut -d'=' -f2)
export POSTGRES_PASSWORD=$(echo "$SECRETS" | grep POSTGRES_PASSWORD | cut -d'=' -f2)

echo "✅ Secrets loaded from Bitwarden"
```

**Usage:**

```bash
# Source the script
source scripts/load_secrets_from_bitwarden.sh

# Or use with dotenv
bw get item "Epstein Project Keys" --session $BW_SESSION | jq -r '.notes' > .env
```

**Documentation:**
- [Bitwarden CLI Documentation](https://bitwarden.com/help/cli/)

## API Key Acquisition

### OpenRouter API Key

OpenRouter provides access to multiple LLM models, including free options.

**Steps to get API key:**

1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Click "Sign In" or "Get Started"
3. Create an account or sign in
4. Go to [Keys](https://openrouter.ai/keys)
5. Click "Create Key"
6. Name your key (e.g., "Epstein Project")
7. Copy the generated key

**Free Models:**

OpenRouter offers several free models. Use our utility to discover them:

```bash
# List free models
python -m epstein.openrouter_models

# Refresh and export
python -m epstein.openrouter_models --refresh --export free_models.json
```

**Pricing:**
- Many models are free
- Paid models charge per token
- Monitor usage at [OpenRouter Dashboard](https://openrouter.ai/activity)

### GitHub Personal Access Token

Required for GitHub API access, creating issues, and CI/CD.

**Steps to create token:**

1. Go to GitHub Settings → [Developer settings](https://github.com/settings/tokens)
2. Click "Personal access tokens" → "Tokens (classic)"
3. Click "Generate new token (classic)"
4. Name: "Epstein Project"
5. Select scopes:
   - `repo` (full control of private repositories)
   - `workflow` (update GitHub Action workflows)
   - `admin:org` (if accessing organization resources)
6. Click "Generate token"
7. **Copy the token immediately** (you won't see it again)

**Alternative: Fine-grained tokens:**

1. Personal access tokens → "Fine-grained tokens"
2. Generate new token
3. Select specific repository
4. Choose specific permissions
5. More secure, recommended for production

### Cloudflare R2 Keys (Optional)

For artifact storage in Cloudflare R2 (S3-compatible).

**Steps:**

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Account Home → R2
3. Create a bucket (if not exists)
4. Click "Manage R2 API Tokens"
5. Click "Create API token"
6. Configure permissions (read/write)
7. Copy Access Key ID and Secret Access Key

## Security Best Practices

### 1. Never Commit Secrets

```bash
# Verify .gitignore includes:
.env
.env.*
*.key
*.pem
secrets/
```

### 2. Use Different Keys per Environment

```bash
# Development
.env.development

# Staging  
.env.staging

# Production
.env.production
```

### 3. Rotate Keys Regularly

- Rotate API keys every 90 days
- Rotate database passwords every 180 days
- Immediately rotate if compromised

### 4. Use Minimum Required Permissions

- GitHub tokens: Only grant needed scopes
- Database users: Read-only where possible
- API keys: Use sub-keys with limited permissions

### 5. Monitor API Usage

```bash
# Check OpenRouter usage
# Visit: https://openrouter.ai/activity

# Monitor GitHub API rate limits
gh api rate_limit
```

### 6. Secret Scanning

```bash
# Install git-secrets
brew install git-secrets  # macOS
# or
apt-get install git-secrets  # Ubuntu

# Setup
git secrets --install
git secrets --register-aws

# Scan repository
git secrets --scan
```

## Troubleshooting

### Issue: "API key not found"

**Solution:**
```bash
# Check if .env file exists
ls -la .env

# Verify environment variables are loaded
python -c "import os; print(os.getenv('OPENROUTER_API_KEY', 'NOT SET'))"

# Manually load .env
source .env  # bash
set -a; source .env; set +a  # more robust
```

### Issue: "Invalid API key"

**Solution:**
```bash
# Verify key format (no extra spaces/quotes)
echo $OPENROUTER_API_KEY | cat -A

# Test API key
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models
```

### Issue: "Permission denied"

**Solution:**
```bash
# Check file permissions
chmod 600 .env

# Check GitHub token scopes
gh auth status

# Regenerate token if needed
```

### Issue: Database connection failed

**Solution:**
```bash
# Test connection
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB

# Check if service is running
docker compose ps postgres

# Check credentials
docker compose logs postgres | grep ERROR
```

## Validation Script

Use this script to validate all API keys are configured:

```bash
#!/bin/bash
# scripts/validate_api_keys.sh

set -e

echo "🔍 Validating API keys and configuration..."

# Load .env if exists
if [ -f .env ]; then
    source .env
fi

ERRORS=0

# Check OpenRouter
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY not set"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ OPENROUTER_API_KEY configured"
fi

# Check GitHub
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN not set (optional for some operations)"
else
    echo "✅ GITHUB_TOKEN configured"
fi

# Check Database
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ POSTGRES_PASSWORD not set"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ POSTGRES_PASSWORD configured"
fi

# Summary
echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All required API keys configured!"
    exit 0
else
    echo "❌ $ERRORS required API key(s) missing"
    echo "Please see docs/API_KEYS_SETUP.md for setup instructions"
    exit 1
fi
```

**Run validation:**
```bash
chmod +x scripts/validate_api_keys.sh
./scripts/validate_api_keys.sh
```

## Additional Resources

- [12-Factor App: Config](https://12factor.net/config)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Python dotenv Documentation](https://saurabh-kumar.com/python-dotenv/)

## Support

If you need help with API key setup:

1. Check this documentation
2. Review `.env.example` for required variables
3. Run `scripts/validate_api_keys.sh` to diagnose issues
4. Open an issue on GitHub with error messages (never include actual keys!)

---

**Last Updated**: 2026-02-01  
**Maintainer**: Epstein Project Team
