import sys
from pathlib import Path

# Ensure the pipeline directory is on sys.path so aggregate.py can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))
