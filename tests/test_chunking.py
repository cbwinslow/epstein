import os
from scripts.chunking import chunk_text_by_sentences


def test_chunking_basic():
    text = "This is sentence one. This is sentence two? And here's sentence three! Short." * 10
    chunks = chunk_text_by_sentences(text, max_chars=200, overlap_chars=40)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) > 0
        assert len(c) <= 200 + 100  # allow slight overshoot


def test_sentence_split_preserves_sentences():
    text = "Hello world. Second sentence. Third one? Final!"
    chunks = chunk_text_by_sentences(text, max_chars=50, overlap_chars=10)
    # ensures sentences are present
    assert any('Hello world.' in c for c in chunks)
    assert any('Second sentence.' in c for c in chunks)
    assert any('Third one?' in c for c in chunks)
    assert any('Final!' in c for c in chunks)
