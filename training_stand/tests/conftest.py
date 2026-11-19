import os
import tempfile
from pathlib import Path

os.environ["STAND_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "stand.db")
os.environ["STAND_RESET_TOKEN"] = "test-reset"
