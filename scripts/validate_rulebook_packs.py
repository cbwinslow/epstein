#!/usr/bin/env python3
"""Validate rulebook pack structure and referenced files.

Checks:
- pack.yaml is valid YAML and contains `starters` with `memory_dir`, `tools_dir`, `rules_file`.
- referenced files/dirs exist under the pack directory.
- simple lint: pack name and version present.

Exit code: 0 on success, 2 on failure.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("PyYAML is required to run this script. Install with: pip install pyyaml")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
PACKS_DIR = ROOT / "rulebook_packs"

errors = []

if not PACKS_DIR.exists():
    print(f"No rulebook_packs directory found at {PACKS_DIR}")
    sys.exit(0)  # nothing to validate

for pack in PACKS_DIR.iterdir():
    if not pack.is_dir():
        continue
    print(f"Validating pack: {pack.name}")
    pack_yaml = pack / "pack.yaml"
    if not pack_yaml.exists():
        errors.append(f"Missing pack.yaml in {pack}")
        continue
    try:
        data = yaml.safe_load(pack_yaml.read_text(encoding="utf-8")) or {}
    except Exception as e:
        errors.append(f"Failed to parse YAML {pack_yaml}: {e}")
        continue

    # Basic keys
    if not data.get("name") or not data.get("version"):
        errors.append(f"pack.yaml in {pack} missing name or version")

    starters = data.get("starters") or {}
    mem = starters.get("memory_dir")
    tools = starters.get("tools_dir")
    rules = starters.get("rules_file")

    if mem:
        mpath = pack / mem
        if not mpath.exists():
            errors.append(f"memory_dir referenced but not found: {mpath}")
    else:
        errors.append(f"pack {pack.name}: starters.memory_dir missing")

    if tools:
        tpath = pack / tools
        if not tpath.exists():
            errors.append(f"tools_dir referenced but not found: {tpath}")
    else:
        errors.append(f"pack {pack.name}: starters.tools_dir missing")

    if rules:
        rpath = pack / rules
        if not rpath.exists():
            errors.append(f"rules_file referenced but not found: {rpath}")
    else:
        errors.append(f"pack {pack.name}: starters.rules_file missing")

if errors:
    print("\nValidation failed with errors:")
    for e in errors:
        print(" - ", e)
    sys.exit(2)

print("All packs validated OK.")
sys.exit(0)
