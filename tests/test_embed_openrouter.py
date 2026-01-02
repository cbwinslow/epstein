import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import numpy as np
from unittest.mock import patch, MagicMock
from scripts.embed_chunks import embed_with_openrouter


def fake_resp_ok(vecs):
    class R:
        def raise_for_status(self):
            return None
        def json(self):
            return {'data': [{'embedding': v} for v in vecs]}
    return R()


def test_embed_with_openrouter_batches():
    texts = [f'text {i}' for i in range(10)]
    vecs = [[float(i)]*3 for i in range(10)]
    with patch('scripts.embed_chunks.requests.post') as mock_post:
        mock_post.return_value = fake_resp_ok(vecs)
        out = embed_with_openrouter('fake-key', 'or-model', texts, batch_size=4)
        assert out.shape == (10, 3)
        assert np.allclose(out[0], np.array(vecs[0]))
