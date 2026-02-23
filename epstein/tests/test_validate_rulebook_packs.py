import tempfile
from pathlib import Path
import shutil
import sys, os

# Ensure repo root is on sys.path so we can import the scripts module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.validate_rulebook_packs import validate_pack, validate_packs


def make_pack(tmpdir: Path, name: str, with_files: bool = True) -> Path:
    p = tmpdir / name
    p.mkdir()
    py = p / "pack.yaml"
    content = {
        "name": name,
        "version": "0.1",
        "starters": {
            "memory_dir": "memory",
            "tools_dir": "tools",
            "rules_file": "rules/RULES.md",
        },
    }
    py.write_text("""name: %s
version: 0.1
starters:
  memory_dir: memory
  tools_dir: tools
  rules_file: rules/RULES.md
""" % name, encoding="utf-8")
    if with_files:
        (p / "memory").mkdir()
        (p / "tools").mkdir()
        rdir = p / "rules"
        rdir.mkdir()
        (rdir / "RULES.md").write_text("# rules\n", encoding="utf-8")
    return p


def test_validate_pack_ok(tmp_path: Path):
    p = make_pack(tmp_path, "good-pack", with_files=True)
    errs = validate_pack(p)
    assert errs == []


def test_validate_pack_missing_files(tmp_path: Path):
    p = make_pack(tmp_path, "bad-pack", with_files=False)
    errs = validate_pack(p)
    assert any("memory_dir" in e for e in errs)
    assert any("tools_dir" in e for e in errs)
    assert any("rules_file" in e for e in errs)


def test_validate_packs(tmp_path: Path):
    make_pack(tmp_path, "good-pack", with_files=True)
    make_pack(tmp_path, "bad-pack", with_files=False)
    errs = validate_packs(tmp_path)
    assert len(errs) >= 3
