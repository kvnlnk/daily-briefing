"""pytest configuration — ensures repo root is on sys.path for integration tests."""
import sys
from pathlib import Path

# Add repo root so `integrations/` and other top-level modules are importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
