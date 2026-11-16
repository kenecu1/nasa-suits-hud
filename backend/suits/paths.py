"""Where the repo's data files live. One place, so tests and tools agree."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("SUITS_DATA_DIR", REPO_ROOT / "data"))
RECORDINGS_DIR = DATA_DIR / "recordings"
