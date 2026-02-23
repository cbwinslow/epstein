"""
Pytest configuration for Epstein project.

This file ensures that Python can find the project modules
by adding the project root to sys.path.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
