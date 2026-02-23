#!/usr/bin/env python3
"""
Comprehensive unit tests for openrouter_models.py

Tests cover:
- Model fetching from API
- Cache management
- Free models filtering
- Error handling
- CLI functionality

Target: 100% code coverage
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'epstein'))
from openrouter_models import (
    ModelInfo,
    ModelsCache,
    get_free_models,
    get_free_model_ids,
    get_free_model_names,
    refresh_free_models_cache,
    fetch_models_from_api,
    clear_cache,
    _load_cache,
    _save_cache,
    CACHE_FILE,
)


@pytest.fixture
def temp_cache_dir(tmp_path, monkeypatch):
    """Create temporary cache directory"""
    cache_dir = tmp_path / ".cache" / "epstein"
    cache_file = cache_dir / "openrouter_free_models.json"
    
    # Patch CACHE_DIR and CACHE_FILE
    import openrouter_models
    monkeypatch.setattr(openrouter_models, 'CACHE_DIR', cache_dir)
    monkeypatch.setattr(openrouter_models, 'CACHE_FILE', cache_file)
    
    return cache_dir


@pytest.fixture
def sample_models():
    """Create sample model data"""
    return [
        ModelInfo(
            id="free-model-1",
            name="Free Model 1",
            description="A free model",
            context_length=4096,
            pricing_prompt=0.0,
            pricing_completion=0.0,
            is_free=True
        ),
        ModelInfo(
            id="paid-model-1",
            name="Paid Model 1",
            description="A paid model",
            context_length=8192,
            pricing_prompt=0.001,
            pricing_completion=0.002,
            is_free=False
        ),
        ModelInfo(
            id="free-model-2",
            name="Free Model 2",
            description="Another free model",
            context_length=2048,
            pricing_prompt=0.0,
            pricing_completion=0.0,
            is_free=True
        ),
    ]


@pytest.fixture
def sample_api_response():
    """Create sample API response"""
    return {
        'data': [
            {
                'id': 'free-model-1',
                'name': 'Free Model 1',
                'description': 'A free model',
                'context_length': 4096,
                'pricing': {'prompt': '0', 'completion': '0'},
                'created': 1234567890,
                'architecture': {'modality': 'text'},
                'top_provider': {'name': 'Provider 1'}
            },
            {
                'id': 'paid-model-1',
                'name': 'Paid Model 1',
                'description': 'A paid model',
                'context_length': 8192,
                'pricing': {'prompt': '0.001', 'completion': '0.002'},
                'created': 1234567891,
                'architecture': {'modality': 'text'},
                'top_provider': {'name': 'Provider 2'}
            },
        ]
    }


class TestModelInfo:
    """Test ModelInfo dataclass"""
    
    def test_create_model_info(self):
        """Test creating ModelInfo instance"""
        model = ModelInfo(
            id="test-model",
            name="Test Model",
            is_free=True
        )
        
        assert model.id == "test-model"
        assert model.name == "Test Model"
        assert model.is_free is True
    
    def test_model_info_to_dict(self):
        """Test converting ModelInfo to dictionary"""
        model = ModelInfo(
            id="test-model",
            name="Test Model",
            context_length=4096,
            is_free=True
        )
        
        model_dict = model.to_dict()
        
        assert model_dict['id'] == "test-model"
        assert model_dict['name'] == "Test Model"
        assert model_dict['context_length'] == 4096
        assert model_dict['is_free'] is True


class TestModelsCache:
    """Test ModelsCache dataclass"""
    
    def test_create_cache(self, sample_models):
        """Test creating ModelsCache instance"""
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        
        assert len(cache.models) == 3
        assert cache.timestamp == now
        assert cache.expires_at == now + 3600
    
    def test_cache_is_expired(self, sample_models):
        """Test checking if cache is expired"""
        now = time.time()
        
        # Not expired
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        assert cache.is_expired() is False
        
        # Expired
        cache = ModelsCache(
            models=sample_models,
            timestamp=now - 7200,
            expires_at=now - 3600
        )
        assert cache.is_expired() is True
    
    def test_cache_to_dict(self, sample_models):
        """Test converting cache to dictionary"""
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        
        cache_dict = cache.to_dict()
        
        assert 'models' in cache_dict
        assert 'timestamp' in cache_dict
        assert 'expires_at' in cache_dict
        assert len(cache_dict['models']) == 3
    
    def test_cache_from_dict(self):
        """Test creating cache from dictionary"""
        now = time.time()
        data = {
            'models': [
                {
                    'id': 'test-model',
                    'name': 'Test Model',
                    'description': '',
                    'context_length': 4096,
                    'pricing_prompt': 0.0,
                    'pricing_completion': 0.0,
                    'is_free': True,
                    'created': 0,
                    'architecture': None,
                    'top_provider': None
                }
            ],
            'timestamp': now,
            'expires_at': now + 3600
        }
        
        cache = ModelsCache.from_dict(data)
        
        assert len(cache.models) == 1
        assert cache.models[0].id == 'test-model'
        assert cache.timestamp == now


class TestCacheOperations:
    """Test cache saving and loading"""
    
    def test_save_and_load_cache(self, temp_cache_dir, sample_models):
        """Test saving and loading cache"""
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        
        # Save cache
        _save_cache(cache)
        
        # Load cache
        loaded_cache = _load_cache()
        
        assert loaded_cache is not None
        assert len(loaded_cache.models) == 3
        assert loaded_cache.timestamp == cache.timestamp
    
    def test_load_nonexistent_cache(self, temp_cache_dir):
        """Test loading cache when file doesn't exist"""
        cache = _load_cache()
        
        assert cache is None
    
    def test_load_expired_cache(self, temp_cache_dir, sample_models):
        """Test loading expired cache"""
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now - 7200,
            expires_at=now - 3600  # Expired 1 hour ago
        )
        
        _save_cache(cache)
        loaded_cache = _load_cache()
        
        assert loaded_cache is None  # Expired cache should be rejected
    
    def test_load_corrupted_cache(self, temp_cache_dir):
        """Test loading corrupted cache file"""
        import openrouter_models
        cache_file = openrouter_models.CACHE_FILE
        
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("not valid json")
        
        cache = _load_cache()
        
        assert cache is None
    
    def test_save_cache_creates_directory(self, temp_cache_dir, sample_models):
        """Test that saving cache creates directory if needed"""
        import openrouter_models
        cache_dir = openrouter_models.CACHE_DIR
        
        # Ensure directory doesn't exist
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
        
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        
        _save_cache(cache)
        
        assert cache_dir.exists()


class TestFetchModelsFromAPI:
    """Test fetching models from OpenRouter API"""
    
    @patch('openrouter_models.requests')
    def test_fetch_models_success(self, mock_requests, sample_api_response):
        """Test successful API fetch"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response
        
        models = fetch_models_from_api()
        
        assert len(models) == 2
        assert models[0].id == 'free-model-1'
        assert models[0].is_free is True
        assert models[1].id == 'paid-model-1'
        assert models[1].is_free is False
    
    @patch('openrouter_models.requests')
    def test_fetch_models_with_api_key(self, mock_requests, sample_api_response, monkeypatch):
        """Test API fetch with API key"""
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
        
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response
        
        fetch_models_from_api()
        
        # Check that API key was included in headers
        call_args = mock_requests.get.call_args
        headers = call_args[1]['headers']
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test-key'
    
    @patch('openrouter_models.requests')
    def test_fetch_models_api_error(self, mock_requests):
        """Test handling API error"""
        import requests
        mock_requests.get.side_effect = requests.RequestException("API Error")
        mock_requests.RequestException = requests.RequestException
        
        with pytest.raises(requests.RequestException):
            fetch_models_from_api()
    
    @patch('openrouter_models.requests', None)
    def test_fetch_models_no_requests_library(self):
        """Test error when requests library not available"""
        with pytest.raises(RuntimeError, match="requests library is required"):
            fetch_models_from_api()


class TestGetFreeModels:
    """Test get_free_models function"""
    
    @patch('openrouter_models.fetch_models_from_api')
    def test_get_free_models_from_api(self, mock_fetch, temp_cache_dir, sample_models):
        """Test getting free models from API (no cache)"""
        mock_fetch.return_value = sample_models
        
        models = get_free_models()
        
        # Should return only free models
        assert len(models) == 2
        assert all(m.is_free for m in models)
    
    def test_get_free_models_from_cache(self, temp_cache_dir, sample_models):
        """Test getting free models from valid cache"""
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        _save_cache(cache)
        
        with patch('openrouter_models.fetch_models_from_api') as mock_fetch:
            models = get_free_models()
            
            # Should not call API
            mock_fetch.assert_not_called()
            
            # Should return only free models
            assert len(models) == 2
            assert all(m.is_free for m in models)
    
    @patch('openrouter_models.fetch_models_from_api')
    def test_get_free_models_force_refresh(self, mock_fetch, temp_cache_dir, sample_models):
        """Test forcing refresh even with valid cache"""
        # Create valid cache
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        _save_cache(cache)
        
        mock_fetch.return_value = sample_models
        
        # Force refresh
        models = get_free_models(force_refresh=True)
        
        # Should call API despite valid cache
        mock_fetch.assert_called_once()
        assert len(models) == 2


class TestRefreshFreeModelsCache:
    """Test refresh_free_models_cache function"""
    
    @patch('openrouter_models.fetch_models_from_api')
    def test_refresh_cache(self, mock_fetch, temp_cache_dir, sample_models):
        """Test refreshing cache"""
        mock_fetch.return_value = sample_models
        
        models = refresh_free_models_cache()
        
        # Should fetch from API
        mock_fetch.assert_called_once()
        
        # Should return only free models
        assert len(models) == 2
        assert all(m.is_free for m in models)
        
        # Cache should be saved
        loaded_cache = _load_cache()
        assert loaded_cache is not None
        assert len(loaded_cache.models) == 3  # All models saved to cache
    
    def test_refresh_cache_with_valid_cache_no_force(self, temp_cache_dir, sample_models):
        """Test refresh with valid cache and force=False"""
        # Create valid cache
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        _save_cache(cache)
        
        with patch('openrouter_models.fetch_models_from_api') as mock_fetch:
            models = refresh_free_models_cache(force=False)
            
            # Should not call API with valid cache
            mock_fetch.assert_not_called()
            assert len(models) == 2
    
    @patch('openrouter_models.fetch_models_from_api')
    def test_refresh_cache_force(self, mock_fetch, temp_cache_dir, sample_models):
        """Test forced cache refresh"""
        # Create valid cache
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        _save_cache(cache)
        
        mock_fetch.return_value = sample_models
        
        # Force refresh
        models = refresh_free_models_cache(force=True)
        
        # Should call API even with valid cache
        mock_fetch.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @patch('openrouter_models.get_free_models')
    def test_get_free_model_ids(self, mock_get_models, sample_models):
        """Test getting free model IDs"""
        free_models = [m for m in sample_models if m.is_free]
        mock_get_models.return_value = free_models
        
        ids = get_free_model_ids()
        
        assert len(ids) == 2
        assert 'free-model-1' in ids
        assert 'free-model-2' in ids
    
    @patch('openrouter_models.get_free_models')
    def test_get_free_model_names(self, mock_get_models, sample_models):
        """Test getting free model names"""
        free_models = [m for m in sample_models if m.is_free]
        mock_get_models.return_value = free_models
        
        names = get_free_model_names()
        
        assert len(names) == 2
        assert names['free-model-1'] == 'Free Model 1'
        assert names['free-model-2'] == 'Free Model 2'


class TestClearCache:
    """Test clear_cache function"""
    
    def test_clear_existing_cache(self, temp_cache_dir, sample_models):
        """Test clearing existing cache"""
        import openrouter_models
        
        # Create cache
        now = time.time()
        cache = ModelsCache(
            models=sample_models,
            timestamp=now,
            expires_at=now + 3600
        )
        _save_cache(cache)
        
        assert openrouter_models.CACHE_FILE.exists()
        
        # Clear cache
        clear_cache()
        
        assert not openrouter_models.CACHE_FILE.exists()
    
    def test_clear_nonexistent_cache(self, temp_cache_dir):
        """Test clearing cache when it doesn't exist"""
        # Should not raise error
        clear_cache()


class TestPrintFreeModels:
    """Test print_free_models function"""
    
    @patch('openrouter_models.get_free_models')
    def test_print_free_models(self, mock_get_models, sample_models, capsys):
        """Test printing free models"""
        from openrouter_models import print_free_models
        
        free_models = [m for m in sample_models if m.is_free]
        mock_get_models.return_value = free_models
        
        print_free_models(verbose=False)
        
        captured = capsys.readouterr()
        assert 'free-model-1' in captured.out
        assert 'free-model-2' in captured.out
        assert 'Found 2 free models' in captured.out
    
    @patch('openrouter_models.get_free_models')
    def test_print_free_models_verbose(self, mock_get_models, sample_models, capsys):
        """Test printing free models with verbose output"""
        from openrouter_models import print_free_models
        
        free_models = [m for m in sample_models if m.is_free]
        mock_get_models.return_value = free_models
        
        print_free_models(verbose=True)
        
        captured = capsys.readouterr()
        assert 'Description:' in captured.out
        assert 'Context Length:' in captured.out


class TestCLI:
    """Test CLI functionality"""
    
    @patch('openrouter_models.get_free_models')
    def test_cli_list_models(self, mock_get_models, sample_models):
        """Test CLI list command"""
        from openrouter_models import main
        
        free_models = [m for m in sample_models if m.is_free]
        mock_get_models.return_value = free_models
        
        with patch('sys.argv', ['openrouter_models']):
            result = main()
        
        assert result == 0
    
    def test_cli_clear_cache(self, temp_cache_dir):
        """Test CLI clear-cache command"""
        from openrouter_models import main
        
        with patch('sys.argv', ['openrouter_models', '--clear-cache']):
            result = main()
        
        assert result == 0
    
    @patch('openrouter_models.get_free_models')
    def test_cli_export(self, mock_get_models, sample_models, tmp_path):
        """Test CLI export command"""
        from openrouter_models import main
        
        free_models = [m for m in sample_models if m.is_free]
        mock_get_models.return_value = free_models
        
        export_file = tmp_path / "models.json"
        
        with patch('sys.argv', ['openrouter_models', '--export', str(export_file)]):
            result = main()
        
        assert result == 0
        assert export_file.exists()
        
        # Check exported data
        with export_file.open() as f:
            data = json.load(f)
        
        assert 'models' in data
        assert 'count' in data
        assert data['count'] == 2
    
    @patch('openrouter_models.get_free_models')
    def test_cli_refresh(self, mock_get_models, sample_models):
        """Test CLI refresh command"""
        from openrouter_models import main
        
        free_models = [m for m in sample_models if m.is_free]
        mock_get_models.return_value = free_models
        
        with patch('sys.argv', ['openrouter_models', '--refresh']):
            result = main()
        
        assert result == 0
        mock_get_models.assert_called_with(force_refresh=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=openrouter_models', '--cov-report=html', '--cov-report=term'])
