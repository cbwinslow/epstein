import subprocess
from pathlib import Path


def run_verify(tmp_path: Path, docs_dir: Path) -> subprocess.CompletedProcess:
    # Use the repository's script, but run it with cwd=tmp_path so it checks the temp project
    repo_script = Path(__file__).resolve().parents[1] / "scripts" / "verify_bundle.sh"
    cmd = ["bash", str(repo_script), str(docs_dir)]
    return subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True)


def test_verify_bundle_ok(tmp_path: Path):
    # create repo layout under tmp_path
    (tmp_path / "project").mkdir()
    # Use project as repo root
    docs = tmp_path / "project" / "docs" / "files" / "bundle1"
    docs.mkdir(parents=True)
    # file path relative to repo root
    rel = Path("bundle1") / "hello.txt"
    (docs / "hello.txt").write_text("hello\n", encoding="utf-8")
    # create target file at repo root matching content
    (tmp_path / "project" / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "project" / rel).write_text("hello\n", encoding="utf-8")

    res = run_verify(tmp_path / "project", Path("docs/files"))
    assert res.returncode == 0
    assert "All bundles verified OK" in res.stdout


def test_verify_bundle_mismatch(tmp_path: Path):
    # create repo layout under tmp_path
    (tmp_path / "project").mkdir()
    docs = tmp_path / "project" / "docs" / "files" / "bundle1"
    docs.mkdir(parents=True)
    rel = Path("bundle1") / "hello.txt"
    (docs / "hello.txt").write_text("hello\n", encoding="utf-8")
    (tmp_path / "project" / rel).parent.mkdir(parents=True, exist_ok=True)
    # different content
    (tmp_path / "project" / rel).write_text("goodbye\n", encoding="utf-8")

    res = run_verify(tmp_path / "project", Path("docs/files"))
    assert res.returncode != 0
    assert "MISMATCH" in res.stdout
