import re
from pathlib import Path

REQUIRED_HEADERS = [
    "Project Overview",
    "Key Technologies & Stack",
    "Docker Development",
]


def test_copilot_instructions_exists() -> None:
    p = Path(".github/copilot-instructions.md")
    assert p.exists(), "Missing .github/copilot-instructions.md"


def test_copilot_instructions_headers() -> None:
    p = Path(".github/copilot-instructions.md")
    text = p.read_text(encoding="utf-8")
    for header in REQUIRED_HEADERS:
        # Case-insensitive substring check to be tolerant of formatting
        assert re.search(re.escape(header), text, re.I), f"Missing required header: {header}"
