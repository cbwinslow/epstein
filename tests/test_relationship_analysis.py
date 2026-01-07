import json
from pathlib import Path

from epstein.relationship_analysis import build_cooccurrence_relationships, write_relationships


def write_entity(path: Path, obj: dict) -> None:
    path.write_text("", encoding="utf-8") if not path.exists() else None
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
    assert rel.entity_a in {"Alice", "Bob"}
    assert rel.entity_b in {"Alice", "Bob"}
    assert rel.count == 1

    output_path = tmp_path / "relationships.jsonl"
    write_relationships(output_path, relationships)
    assert output_path.read_text(encoding="utf-8").strip()
