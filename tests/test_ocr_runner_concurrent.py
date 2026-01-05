import os
import json
import multiprocessing
from pathlib import Path


def worker(proc_id: int, count: int, root: str):
    # Set environment to point to a fresh workspace for child process
    os.environ['EPSTEIN_ROOT_OVERRIDE'] = root
    # Ensure the project root is on sys.path so child processes can import `scripts`
    import sys
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    # Import inside worker to ensure module-level state uses the overridden root
    from scripts.ocr_runner import atomic_append_status, STATUS_FILE
    for i in range(count):
        atomic_append_status({'proc': proc_id, 'i': i})


def test_concurrent_appends(tmp_path):
    root = tmp_path / 'epstein'
    (root / 'epstein_project').mkdir(parents=True)

    N = 4
    M = 25
    procs = []
    for p in range(N):
        proc = multiprocessing.Process(target=worker, args=(p, M, str(root)))
        proc.start()
        procs.append(proc)

    for proc in procs:
        # Wait for process completion (blocking) to avoid flaky timeouts in CI
        proc.join()
        assert proc.exitcode == 0, f"Process exited with {proc.exitcode}"

    status_file = root / 'epstein_project' / 'processing_status.jsonl'
    assert status_file.exists(), "Status file not created"
    lines = [l for l in status_file.read_text(encoding='utf-8').splitlines() if l.strip()]
    assert len(lines) == N * M

    pairs = set()
    for l in lines:
        obj = json.loads(l)
        pairs.add((obj['proc'], obj['i']))
    assert len(pairs) == N * M
