import json
from pathlib import Path

from epstein.relationship_analysis import build_cooccurrence_relationships, write_relationships


def write_entity(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj) + "\n")


def test_build_relationships_from_entities(tmp_path: Path) -> None:
    entities_dir = tmp_path / "entities"
    entities_dir.mkdir()
    file_path = entities_dir / "doc1.entities.jsonl"

    write_entity(
        file_path,
        {
            "doc_id": "doc1",
            "label": "PERSON",
            "text": "Alice",
            "chunk_id": "1",
            "source_url": "https://example.com/doc1.pdf",
        },
    )
    write_entity(
        file_path,
        {
            "doc_id": "doc1",
            "label": "PERSON",
            "text": "Bob",
            "chunk_id": "1",
            "source_url": "https://example.com/doc1.pdf",
        },
    )

    relationships = build_cooccurrence_relationships(entities_dir, min_count=1)
    assert len(relationships) == 1
    rel = relationships[0]
    assert {rel.entity_a, rel.entity_b} == {"Alice", "Bob"}
    assert rel.count == 1

    output_path = tmp_path / "relationships.jsonl"
    write_relationships(output_path, relationships)
    
    # Validate JSONL output structure
    content = output_path.read_text(encoding="utf-8").strip()
    assert content
    parsed = json.loads(content)
    assert parsed["relationship_type"] == "CO_OCCURS"
    assert parsed["entity_a"] in {"Alice", "Bob"}
    assert parsed["entity_b"] in {"Alice", "Bob"}
    assert parsed["count"] == 1
    assert "evidence" in parsed
    assert "doc_ids" in parsed
