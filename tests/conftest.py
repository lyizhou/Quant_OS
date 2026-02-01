"""Test configuration and fixtures for pytest."""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "drivers"))
sys.path.insert(0, str(project_root / "core"))

# Test configuration
pytest_plugins = []
