#!/usr/bin/env python3
"""Simple chunking utility with overlap.
Creates a JSONL file with chunks given an input text file.
"""
import argparse
import json
from pathlib import Path


def sentence_split(text):
    # simple sentence splitter - splits on ., ?, ! followed by whitespace and capital
    import re
    parts = [s.strip() for s in re.split(r'(?<=[\.\?!])\s+', text) if s.strip()]
    return parts


def chunk_text_by_sentences(text, max_chars=3000, overlap_chars=600):
    sentences = sentence_split(text)
    chunks = []
    cur = []
    cur_len = 0
    for s in sentences:
        if cur_len + len(s) + 1 <= max_chars:
            cur.append(s)
            cur_len += len(s) + 1
        else:
            chunks.append(' '.join(cur))
            # start with overlap
            if overlap_chars > 0:
                # include tail of previous chunk by chars (approx)
                tail = ' '.join(cur)[-overlap_chars:]
                cur = [tail, s]
                cur_len = len(tail) + len(s) + 1
            else:
                cur = [s]
                cur_len = len(s) + 1
    if cur:
        chunks.append(' '.join(cur))
    return chunks


def main(input_text, out_jsonl, max_chars, overlap_chars):
    txt = Path(input_text).read_text(encoding='utf-8')
    chunks = chunk_text_by_sentences(txt, max_chars=max_chars, overlap_chars=overlap_chars)
    out = Path(out_jsonl)
    with out.open('w', encoding='utf-8') as fh:
        for i, c in enumerate(chunks):
            rec = {
                'chunk_id': i,
                'char_start': None,
                'char_end': None,
                'preview': c[:200],
                'text': c
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f'Wrote {len(chunks)} chunks to {out}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input_text')
    p.add_argument('out_jsonl')
    p.add_argument('--max-chars', type=int, default=3000)
    p.add_argument('--overlap-chars', type=int, default=600)
    args = p.parse_args()
    main(args.input_text, args.out_jsonl, args.max_chars, args.overlap_chars)
