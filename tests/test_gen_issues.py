import json
import subprocess


def test_gen_issues_writes_files(tmp_path):
    outjson = tmp_path / "issues.json"
    outmd = tmp_path / "MASTER_TASKS.md"
    import sys

    cmd = [
        sys.executable,
        "scripts/gen_issues_from_tasks.py",
        "--in",
        "tasks/master_tasks.yml",
        "--out-json",
        str(outjson),
        "--out-md",
        str(outmd),
        "--dry-run",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
    assert res.returncode == 0
    assert outjson.exists()
    data = json.loads(outjson.read_text())
    assert isinstance(data, list)
    assert len(data) > 0
