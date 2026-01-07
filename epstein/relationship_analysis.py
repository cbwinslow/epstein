#!/usr/bin/env python3
"""Relationship analysis utilities for entity co-occurrence."""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class EntityMention:
    doc_id: str
    label: str
    text: str
    chunk_id: str
    source_url: Optional[str]


@dataclass
class Relationship:
    entity_a: str
    entity_b: str
    label_a: str
    label_b: str
    count: int
    doc_ids: List[str]
    evidence: List[dict]


def normalize_entity(text: str, normalize_case: bool = True) -> str:
    cleaned = " ".join(text.split())
    return cleaned.casefold() if normalize_case else cleaned


def iter_entity_mentions(entities_dir: Path) -> Iterable[EntityMention]:
    for path in sorted(entities_dir.glob("*.entities.jsonl")):
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                doc_id = str(obj.get("doc_id", ""))
                label = str(obj.get("label", ""))
                text = str(obj.get("text", "")).strip()
                chunk_id = str(obj.get("chunk_id", ""))
                source_url = obj.get("source_url")
                if not doc_id or not label or not text or not chunk_id:
                    continue
                yield EntityMention(
                    doc_id=doc_id,
                    label=label,
                    text=text,
                    chunk_id=chunk_id,
                    source_url=str(source_url) if source_url else None,
                )


def build_cooccurrence_relationships(
    entities_dir: Path,
    min_count: int = 2,
    max_evidence: int = 5,
    normalize_case: bool = True,
) -> List[Relationship]:
    chunk_map: Dict[Tuple[str, str], List[EntityMention]] = {}
    for mention in iter_entity_mentions(entities_dir):
        key = (mention.doc_id, mention.chunk_id)
        chunk_map.setdefault(key, []).append(mention)

    counts: Dict[Tuple[str, str, str, str], Relationship] = {}

    for (doc_id, chunk_id), mentions in chunk_map.items():
        unique_entities: Dict[str, EntityMention] = {}
        for mention in mentions:
            key = f"{mention.label}:{normalize_entity(mention.text, normalize_case)}"
            if key not in unique_entities:
                unique_entities[key] = mention

        if len(unique_entities) < 2:
            continue

        for a_key, b_key in itertools.combinations(sorted(unique_entities), 2):
            a = unique_entities[a_key]
            b = unique_entities[b_key]
            rel_key = (a_key, b_key, a.label, b.label)
            rel = counts.get(rel_key)
            if rel is None:
                rel = Relationship(
                    entity_a=a.text,
                    entity_b=b.text,
                    label_a=a.label,
                    label_b=b.label,
                    count=0,
                    doc_ids=[],
                    evidence=[],
                )
                counts[rel_key] = rel

            rel.count += 1
            if doc_id not in rel.doc_ids:
                rel.doc_ids.append(doc_id)
            if len(rel.evidence) < max_evidence:
                rel.evidence.append(
                    {
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "source_url": a.source_url or b.source_url,
                    }
                )

    relationships = [rel for rel in counts.values() if rel.count >= min_count]
    relationships.sort(key=lambda r: (-r.count, r.entity_a, r.entity_b))
    return relationships


def write_relationships(output_path: Path, relationships: List[Relationship]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for rel in relationships:
            handle.write(
                json.dumps(
                    {
                        "relationship_type": "CO_OCCURS",
                        "entity_a": rel.entity_a,
                        "entity_b": rel.entity_b,
                        "label_a": rel.label_a,
                        "label_b": rel.label_b,
                        "count": rel.count,
                        "doc_ids": rel.doc_ids,
                        "evidence": rel.evidence,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def run_relationship_analysis(
    entities_dir: Path,
    output_path: Path,
    min_count: int = 2,
    max_evidence: int = 5,
    normalize_case: bool = True,
) -> int:
    relationships = build_cooccurrence_relationships(
        entities_dir,
        min_count=min_count,
        max_evidence=max_evidence,
        normalize_case=normalize_case,
    )
    write_relationships(output_path, relationships)
    return len(relationships)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build co-occurrence relationships from entity JSONL.")
    ap.add_argument("--entities-dir", default="./epstein_artifacts/entities")
    ap.add_argument("--out", default="./epstein_artifacts/relationships/relationships.jsonl")
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--max-evidence", type=int, default=5)
    ap.add_argument("--no-normalize-case", action="store_true")
    args = ap.parse_args()

    entities_dir = Path(args.entities_dir).expanduser().resolve()
    output_path = Path(args.out).expanduser().resolve()

    if not entities_dir.exists():
        raise SystemExit(f"Entities dir not found: {entities_dir}")

    total = run_relationship_analysis(
        entities_dir=entities_dir,
        output_path=output_path,
        min_count=args.min_count,
        max_evidence=args.max_evidence,
        normalize_case=not args.no_normalize_case,
    )
    print(f"[relationships] wrote {total} relationships to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
