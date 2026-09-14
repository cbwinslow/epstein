#!/usr/bin/env python3
"""
OpenRouter Free Models Discovery

This module provides functionality to discover and manage free models
available on OpenRouter.ai. It fetches the current list of free models
and maintains an up-to-date registry that can be used by other parts
of the application.

Usage:
    from epstein.openrouter_models import get_free_models, refresh_free_models_cache

    # Get free models (uses cache if available)
    models = get_free_models()

    # Force refresh cache
    models = refresh_free_models_cache()

Configuration:
    Set OPENROUTER_API_KEY environment variable or use .env file

Environment Variables:
    OPENROUTER_API_KEY - Your OpenRouter API key (optional for listing)
    OPENROUTER_BASE_URL - Base URL (default: https://openrouter.ai/api/v1)
    OPENROUTER_MODELS_CACHE_TTL - Cache TTL in seconds (default: 3600)
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_CACHE_TTL = 3600  # 1 hour
MODELS_ENDPOINT = "/models"
CACHE_DIR = Path.home() / ".cache" / "epstein"
CACHE_FILE = CACHE_DIR / "openrouter_free_models.json"


@dataclass
class ModelInfo:
    """Information about an OpenRouter model"""

    id: str
    name: str
    description: str = ""
    context_length: int = 0
    pricing_prompt: float = 0.0
    pricing_completion: float = 0.0
    is_free: bool = False
    created: int = 0
    architecture: str | None = None
    top_provider: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ModelsCache:
    """Cache for OpenRouter models"""

    models: list[ModelInfo]
    timestamp: float
    expires_at: float

    def is_expired(self) -> bool:
        """Check if cache is expired"""
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "models": [m.to_dict() for m in self.models],
            "timestamp": self.timestamp,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelsCache":
        """Create from dictionary"""
        models = [ModelInfo(**m) for m in data.get("models", [])]
        return cls(
            models=models, timestamp=data.get("timestamp", 0), expires_at=data.get("expires_at", 0)
        )


def _get_base_url() -> str:
    """Get OpenRouter base URL from environment or use default"""
    return os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)


def _get_cache_ttl() -> int:
    """Get cache TTL from environment or use default"""
    try:
        return int(os.getenv("OPENROUTER_MODELS_CACHE_TTL", DEFAULT_CACHE_TTL))
    except ValueError:
        return DEFAULT_CACHE_TTL


def _load_cache() -> ModelsCache | None:
    """
    Load models cache from disk.

    Returns:
        ModelsCache object if cache exists and is valid, None otherwise
    """
    if not CACHE_FILE.exists():
        logger.debug(f"Cache file does not exist: {CACHE_FILE}")
        return None

    try:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        cache = ModelsCache.from_dict(data)

        if cache.is_expired():
            logger.info("Cache is expired")
            return None

        logger.info(f"Loaded {len(cache.models)} models from cache")
        return cache

    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def _save_cache(cache: ModelsCache) -> None:
    """
    Save models cache to disk.

    Args:
        cache: ModelsCache object to save
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(cache.to_dict(), f, indent=2)

        logger.info(f"Saved {len(cache.models)} models to cache")

    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def fetch_models_from_api() -> list[ModelInfo]:
    """
    Fetch models from OpenRouter API.

    Returns:
        List of ModelInfo objects

    Raises:
        RuntimeError: If requests library is not available
        requests.RequestException: If API request fails
    """
    if requests is None:
        raise RuntimeError("requests library is required. Install it with: pip install requests")

    base_url = _get_base_url()
    url = f"{base_url}{MODELS_ENDPOINT}"

    headers = {
        "Content-Type": "application/json",
    }

    # Add API key if available
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    logger.info(f"Fetching models from {url}")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        models_data = data.get("data", [])

        logger.info(f"Fetched {len(models_data)} models from API")

        models = []
        for model_data in models_data:
            # Parse pricing
            pricing = model_data.get("pricing", {})
            prompt_price = float(pricing.get("prompt", "0"))
            completion_price = float(pricing.get("completion", "0"))
            is_free = prompt_price == 0.0 and completion_price == 0.0

            model = ModelInfo(
                id=model_data.get("id", ""),
                name=model_data.get("name", ""),
                description=model_data.get("description", ""),
                context_length=model_data.get("context_length", 0),
                pricing_prompt=prompt_price,
                pricing_completion=completion_price,
                is_free=is_free,
                created=model_data.get("created", 0),
                architecture=model_data.get("architecture", {}).get("modality"),
                top_provider=(
                    model_data.get("top_provider", {}).get("name")
                    if model_data.get("top_provider")
                    else None
                ),
            )
            models.append(model)

        return models

    except requests.RequestException as e:
        logger.error(f"Failed to fetch models from API: {e}")
        raise

    except Exception as e:
        logger.error(f"Error parsing models response: {e}")
        raise


def refresh_free_models_cache(force: bool = False) -> list[ModelInfo]:
    """
    Refresh the free models cache by fetching from API.

    Args:
        force: Force refresh even if cache is valid

    Returns:
        List of ModelInfo objects (all free models)
    """
    # Check if cache is valid and force is not set
    if not force:
        cache = _load_cache()
        if cache is not None and not cache.is_expired():
            logger.info("Using valid cache, skipping refresh")
            return [m for m in cache.models if m.is_free]

    # Fetch from API
    logger.info("Refreshing models cache from API")
    all_models = fetch_models_from_api()

    # Save to cache
    now = time.time()
    ttl = _get_cache_ttl()
    cache = ModelsCache(models=all_models, timestamp=now, expires_at=now + ttl)
    _save_cache(cache)

    # Return only free models
    free_models = [m for m in all_models if m.is_free]
    logger.info(f"Found {len(free_models)} free models out of {len(all_models)} total")

    return free_models


def get_free_models(force_refresh: bool = False) -> list[ModelInfo]:
    """
    Get list of free models from OpenRouter.

    Uses cache if available and not expired, otherwise fetches from API.

    Args:
        force_refresh: Force refresh from API even if cache is valid

    Returns:
        List of ModelInfo objects for free models
    """
    # Try to load from cache first
    if not force_refresh:
        cache = _load_cache()
        if cache is not None and not cache.is_expired():
            free_models = [m for m in cache.models if m.is_free]
            logger.info(f"Returning {len(free_models)} free models from cache")
            return free_models

    # Cache miss or expired, refresh
    return refresh_free_models_cache(force=force_refresh)


def get_free_model_ids() -> list[str]:
    """
    Get list of free model IDs.

    Convenience function that returns just the model IDs.

    Returns:
        List of model ID strings
    """
    models = get_free_models()
    return [m.id for m in models]


def get_free_model_names() -> dict[str, str]:
    """
    Get dictionary mapping model IDs to names.

    Returns:
        Dictionary of {model_id: model_name}
    """
    models = get_free_models()
    return {m.id: m.name for m in models}


def print_free_models(verbose: bool = False) -> None:
    """
    Print free models to console.

    Args:
        verbose: Print detailed information about each model
    """
    models = get_free_models()

    print(f"\n🆓 Found {len(models)} free models on OpenRouter:\n")
    print("=" * 80)

    for i, model in enumerate(models, 1):
        if verbose:
            print(f"\n{i}. {model.name}")
            print(f"   ID: {model.id}")
            if model.description:
                print(f"   Description: {model.description}")
            print(f"   Context Length: {model.context_length:,}")
            if model.architecture:
                print(f"   Architecture: {model.architecture}")
            if model.top_provider:
                print(f"   Provider: {model.top_provider}")
        else:
            print(f"{i:3d}. {model.id:50s} | {model.name}")

    print("\n" + "=" * 80)


def clear_cache() -> None:
    """Clear the models cache."""
    if CACHE_FILE.exists():
        try:
            CACHE_FILE.unlink()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    else:
        logger.info("No cache to clear")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Discover and manage free models on OpenRouter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List free models
  python -m epstein.openrouter_models

  # List with detailed information
  python -m epstein.openrouter_models --verbose

  # Force refresh cache
  python -m epstein.openrouter_models --refresh

  # Clear cache
  python -m epstein.openrouter_models --clear-cache

  # Export to JSON
  python -m epstein.openrouter_models --export models.json
        """,
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print detailed model information"
    )
    parser.add_argument("--refresh", "-r", action="store_true", help="Force refresh cache from API")
    parser.add_argument("--clear-cache", action="store_true", help="Clear the models cache")
    parser.add_argument(
        "--export", "-e", type=Path, metavar="FILE", help="Export models to JSON file"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Handle commands
    if args.clear_cache:
        clear_cache()
        print("✅ Cache cleared")
        return 0

    try:
        # Get models
        models = get_free_models(force_refresh=args.refresh)

        # Print models
        print_free_models(verbose=args.verbose)

        # Export if requested
        if args.export:
            export_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "count": len(models),
                "models": [m.to_dict() for m in models],
            }

            args.export.parent.mkdir(parents=True, exist_ok=True)
            with args.export.open("w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)

            print(f"\n💾 Exported {len(models)} models to {args.export}")

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
