from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LIBRARY_BOOKS = ROOT / "library" / "books"
LIBRARY_NOTES = ROOT / "library" / "notes"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "library.db"


def ensure_dirs() -> None:
    LIBRARY_BOOKS.mkdir(parents=True, exist_ok=True)
    LIBRARY_NOTES.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
