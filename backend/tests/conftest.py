import sys
from pathlib import Path

# backend/ on sys.path so tests import `app.*` like the container does.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
