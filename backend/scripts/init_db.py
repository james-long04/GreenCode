#!/usr/bin/env python3
"""Create the evidence-store tables and seed reference data (idempotent)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print("evidence store ready")
