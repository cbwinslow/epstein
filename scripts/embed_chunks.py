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


def embed_with_openrouter(api_key, texts):
    # placeholder: currently not implemented; in CI prefer local model.
    raise NotImplementedError('OpenRouter embedding not implemented in this runner')


def main(model_name='all-MiniLM-L6-v2'):
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
