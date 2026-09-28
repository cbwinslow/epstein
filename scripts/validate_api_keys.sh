#!/bin/bash
# scripts/validate_api_keys.sh
#
# Validates that all required API keys and configuration are properly set
# Provides helpful error messages if anything is missing

set -e

echo "🔍 Validating API keys and configuration..."
printf '=%.0s' {1..70}
echo ""

# Load .env if it exists
if [ -f .env ]; then
    echo "📄 Loading .env file..."
    set -a
    source .env
    set +a
else
    echo "⚠️  No .env file found (will check environment variables)"
fi

ERRORS=0
WARNINGS=0

echo ""
echo "Required Configuration:"
printf -- '-%.0s' {1..70}
echo ""

# Check OpenRouter (required for AI features)
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY not set"
    echo "   Get your key at: https://openrouter.ai/keys"
    echo "   Add to .env: OPENROUTER_API_KEY=your_key_here"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ OPENROUTER_API_KEY configured"
    # Validate format (basic check)
    if [ ${#OPENROUTER_API_KEY} -lt 20 ]; then
        echo "   ⚠️  Warning: Key seems too short, may be invalid"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check Database Configuration (required)
echo ""
echo "Database Configuration:"
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ POSTGRES_PASSWORD not set"
    echo "   Set in .env: POSTGRES_PASSWORD=your_secure_password"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ POSTGRES_PASSWORD configured"
fi

if [ -z "$POSTGRES_HOST" ]; then
    echo "⚠️  POSTGRES_HOST not set (defaulting to localhost)"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ POSTGRES_HOST: $POSTGRES_HOST"
fi

if [ -z "$POSTGRES_DB" ]; then
    echo "⚠️  POSTGRES_DB not set (defaulting to 'analysis')"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ POSTGRES_DB: $POSTGRES_DB"
fi

# Check Optional Configuration
echo ""
echo "Optional Configuration:"
printf -- '-%.0s' {1..70}
echo ""

# GitHub Token (optional for some operations)
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN not set"
    echo "   Required for: Creating issues, accessing private repos"
    echo "   Get token at: https://github.com/settings/tokens"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ GITHUB_TOKEN configured"
fi

# Qdrant Configuration (optional auth)
if [ -z "$QDRANT_API_KEY" ]; then
    echo "ℹ️  QDRANT_API_KEY not set (OK for local development)"
else
    echo "✅ QDRANT_API_KEY configured"
fi

if [ -z "$QDRANT_HOST" ]; then
    echo "ℹ️  QDRANT_HOST not set (defaulting to localhost)"
else
    echo "✅ QDRANT_HOST: $QDRANT_HOST"
fi

# OpenTelemetry (optional)
if [ -z "$OTEL_ENABLED" ] || [ "$OTEL_ENABLED" = "false" ]; then
    echo "ℹ️  OpenTelemetry not enabled (set OTEL_ENABLED=true to enable)"
else
    echo "✅ OpenTelemetry enabled"
    if [ -z "$OTEL_EXPORTER_OTLP_ENDPOINT" ]; then
        echo "   ⚠️  OTEL_EXPORTER_OTLP_ENDPOINT not set"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Cloudflare R2 (optional)
if [ -n "$CLOUDFLARE_R2_ACCESS_KEY_ID" ]; then
    echo "✅ Cloudflare R2 configured"
else
    echo "ℹ️  Cloudflare R2 not configured (optional for artifact storage)"
fi

# Test API Connections
echo ""
echo "Connection Tests:"
printf -- '-%.0s' {1..70}
echo ""

# Test OpenRouter connection (if key is set)
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo "🔌 Testing OpenRouter API..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $OPENROUTER_API_KEY" \
        -H "Content-Type: application/json" \
        https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ OpenRouter API connection successful"
    elif [ "$HTTP_CODE" = "401" ]; then
        echo "   ❌ OpenRouter API key is invalid"
        ERRORS=$((ERRORS + 1))
    elif [ "$HTTP_CODE" = "000" ]; then
        echo "   ⚠️  Could not connect to OpenRouter (network issue?)"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "   ⚠️  Unexpected response from OpenRouter: $HTTP_CODE"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Test Database connection (if docker is running)
if command -v docker &> /dev/null; then
    echo "🔌 Testing Database connection..."

    # Check if postgres container is running
    if docker ps --format '{{.Names}}' | grep -q postgres; then
        DB_HOST=${POSTGRES_HOST:-localhost}
        DB_PORT=${POSTGRES_PORT:-5432}
        DB_NAME=${POSTGRES_DB:-analysis}
        DB_USER=${POSTGRES_USER:-analysis}

        # Try to connect (using docker exec if available)
        if docker exec -i $(docker ps --format '{{.Names}}' | grep postgres | head -1) \
            psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &> /dev/null; then
            echo "   ✅ Database connection successful"
        else
            echo "   ⚠️  Could not connect to database"
            echo "      Check credentials and ensure database is initialized"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "   ℹ️  PostgreSQL container not running"
        echo "      Start with: docker compose up postgres"
    fi
else
    echo "   ℹ️  Docker not available, skipping database test"
fi

# Summary
echo ""
printf '=%.0s' {1..70}
echo ""
echo "📊 Validation Summary"
printf '=%.0s' {1..70}
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ All checks passed! Configuration is complete."
    echo ""
    echo "Next steps:"
    echo "  1. Run: make bootstrap"
    echo "  2. Run: python scripts/epstein_bulk_downloader.py"
    echo "  3. Run: make pipeline-run"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "✅ Required configuration is complete"
    echo "⚠️  $WARNINGS warning(s) - optional configuration missing or issues detected"
    echo ""
    echo "You can proceed, but some features may be limited."
    echo "Review warnings above and update configuration as needed."
    exit 0
else
    echo "❌ $ERRORS error(s) detected - required configuration missing"
    if [ $WARNINGS -gt 0 ]; then
        echo "⚠️  $WARNINGS warning(s) - optional configuration issues"
    fi
    echo ""
    echo "Please fix the errors above before proceeding."
    echo "See docs/API_KEYS_SETUP.md for detailed setup instructions."
    echo ""
    echo "Quick fix:"
    echo "  1. Copy: cp .env.example .env"
    echo "  2. Edit: nano .env"
    echo "  3. Rerun: ./scripts/validate_api_keys.sh"
    exit 1
fi
