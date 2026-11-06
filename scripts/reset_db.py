"""Reset the working database to the untouched original.

Run before every full ticket-resolution run:
    python scripts/reset_db.py
"""

import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
ORIGINAL = DATA / "campus_customs.db"
WORKING = DATA / "campus_customs_new.db"

if not ORIGINAL.exists():
    raise SystemExit(f"Original database missing: {ORIGINAL}")
shutil.copyfile(ORIGINAL, WORKING)
print(f"Reset {WORKING.name} from {ORIGINAL.name}")
