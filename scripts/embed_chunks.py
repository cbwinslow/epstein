#!/usr/bin/env python3
"""Embed chunks using SentenceTransformers or OpenRouter embeddings.

Writes per-chunk embeddings to `epstein_project/embeddings/<sha>.npy` and a metadata JSON.
"""
import os
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_DIR = ROOT / 'epstein_project' / 'chunks'
EMB_DIR = ROOT / 'epstein_project' / 'embeddings'
EMB_DIR.mkdir(parents=True, exist_ok=True)


def embed_with_st(model_name, texts):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model_name)
    return m.encode(texts, batch_size=64, show_progress_bar=False)


def embed_with_openrouter(api_key, model, texts, batch_size=64):
    import requests
    endpoint = os.environ.get('OPENROUTER_API_URL', 'https://api.openrouter.ai/v1/embeddings')
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        payload = {'model': model, 'input': batch}
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # support variants of response schema
        if 'data' in data and isinstance(data['data'], list):
            for item in data['data']:
                emb = item.get('embedding') or item.get('embedding') or item.get('vector')
                embeddings.append(emb)
        elif 'embeddings' in data and isinstance(data['embeddings'], list):
            for emb in data['embeddings']:
                embeddings.append(emb)
        else:
            # try to parse as openai-like
            if 'data' in data and data['data'] and isinstance(data['data'][0], dict) and 'embedding' in data['data'][0]:
                for item in data['data']:
                    embeddings.append(item['embedding'])
            else:
                raise RuntimeError('Unexpected OpenRouter embedding response: %s' % (str(data)[:200]))
    return np.array(embeddings, dtype=np.float32)


def main(model_name='all-MiniLM-L6-v2'):
    # determine embedding backend
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    use_openrouter = False
    openrouter_model = None
    if model_name.startswith('openrouter:'):
        use_openrouter = True
        openrouter_model = model_name.split(':',1)[1]
    elif openrouter_key and model_name.startswith('or-'):
        use_openrouter = True
        openrouter_model = model_name

    # process each chunks jsonl file
    for f in CHUNKS_DIR.glob('*.chunks.jsonl'):
        sha = f.stem.split('.')[0]
        texts = []
        metas = []
        for line in f.open('r', encoding='utf-8'):
            try:
                obj = json.loads(line)
                texts.append(obj.get('text',''))
                metas.append({'chunk_id': obj.get('chunk_id'), 'preview': obj.get('preview')})
            except Exception:
                continue
        if not texts:
            continue
        if use_openrouter:
            api_key = os.environ.get('OPENROUTER_API_KEY')
            if not api_key:
                raise RuntimeError('OPENROUTER_API_KEY not set')
            vecs = embed_with_openrouter(api_key, openrouter_model, texts)
        else:
            vecs = embed_with_st(model_name, texts)
        out_npy = EMB_DIR / f'{sha}.npy'
        np.save(out_npy, vecs)
        meta_out = EMB_DIR / f'{sha}.meta.json'
        meta_out.write_text(json.dumps({'model': model_name, 'count': len(texts)}, indent=2), encoding='utf-8')
        print('Wrote', out_npy)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--model', default='all-MiniLM-L6-v2')
    args = p.parse_args()
    main(args.model)
