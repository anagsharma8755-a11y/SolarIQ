"""Project-wide pytest configuration.

Ensures the project root is on sys.path so that both
``backend.*`` and ``data_pipeline.*`` packages are importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
