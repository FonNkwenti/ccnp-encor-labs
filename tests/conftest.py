import sys
from pathlib import Path

# Make labs/common/tools importable from any test file
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "labs" / "common" / "tools"))
