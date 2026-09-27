from __future__ import annotations

from pathlib import Path

import pytest

from apple_lover_library.enums import RightsBasis
from apple_lover_library.import_local import import_local
from apple_lover_library.store import connect, list_books


def test_import_copies_epub_and_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import apple_lover_library.import_local as mod
    import apple_lover_library.paths as paths

    books = tmp_path / "books"
    data = tmp_path / "data"
    monkeypatch.setattr(paths, "LIBRARY_BOOKS", books)
    monkeypatch.setattr(paths, "DATA_DIR", data)
    monkeypatch.setattr(paths, "DB_PATH", data / "library.db")
    monkeypatch.setattr(mod, "LIBRARY_BOOKS", books)

    src = tmp_path / "sample.epub"
    src.write_bytes(b"PK\x03\x04fake-epub")
    db = data / "library.db"
    book = import_local(
        src,
        title_en="Sample Book",
        author="Jane Tester",
        rights_basis=RightsBasis.LICENSED,
        db_path=db,
    )
    assert book.file_path
    assert Path(book.file_path).is_file()
    assert book.sha256
    assert "Jane Tester" in book.file_path
    with connect(db) as conn:
        assert len(list_books(conn)) == 1
