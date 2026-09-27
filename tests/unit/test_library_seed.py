from __future__ import annotations

from pathlib import Path

import pytest

from apple_lover_library.enums import RightsBasis
from apple_lover_library.seed import seed_companion_notes
from apple_lover_library.store import connect, notes_for


def test_cathedral_is_unknown_with_notes_not_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import apple_lover_library.paths as paths
    import apple_lover_library.seed as seed

    notes_dir = tmp_path / "notes"
    data = tmp_path / "data"
    src = tmp_path / "src"
    src.mkdir()
    (src / "01-introduction-en.txt").write_text("intro", encoding="utf-8")
    (src / "02-reading-guide-en.txt").write_text("guide", encoding="utf-8")
    (src / "Conversation_in_the_Cathedral_-_Mario_Vargas_Llosa.pdf").write_bytes(b"%PDF-fake")

    monkeypatch.setattr(paths, "LIBRARY_NOTES", notes_dir)
    monkeypatch.setattr(paths, "DATA_DIR", data)
    monkeypatch.setattr(paths, "DB_PATH", data / "library.db")
    monkeypatch.setattr(seed, "LIBRARY_NOTES", notes_dir)
    monkeypatch.setattr(seed, "SOURCE_NOTES", src)

    book = seed_companion_notes(db_path=data / "library.db")
    assert book is not None
    assert book.rights_basis is RightsBasis.UNKNOWN
    assert book.file_path is None
    with connect(data / "library.db") as conn:
        notes = notes_for(conn, book.book_id)
    assert {n.kind.value for n in notes} >= {"INTRO", "GUIDE"}
    assert not list(notes_dir.rglob("*.pdf"))


def test_cardone_notes_sit_with_imported_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import apple_lover_library.paths as paths
    import apple_lover_library.seed as seed
    from apple_lover_library.enums import BookSource
    from apple_lover_library.ids import new_id
    from apple_lover_library.models import Book
    from apple_lover_library.store import upsert_book

    notes_dir = tmp_path / "notes"
    data = tmp_path / "data"
    src = tmp_path / "cardone-src"
    src.mkdir()
    (src / "01-introduction-en.txt").write_text("intro", encoding="utf-8")
    (src / "02-reading-guide-en.txt").write_text("guide", encoding="utf-8")
    (src / "03-mind-map.png").write_bytes(b"png")
    (src / "04-cover.png").write_bytes(b"png")
    (src / "README.md").write_text("readme", encoding="utf-8")

    folder = tmp_path / "books" / "Grant Cardone" / "if you're not first you're last"
    folder.mkdir(parents=True)
    pdf = folder / "upload.pdf"
    pdf.write_bytes(b"%PDF-fake")

    monkeypatch.setattr(paths, "LIBRARY_NOTES", notes_dir)
    monkeypatch.setattr(paths, "DATA_DIR", data)
    monkeypatch.setattr(paths, "DB_PATH", data / "library.db")
    monkeypatch.setattr(seed, "SOURCE_CARDONE", src)
    monkeypatch.setattr(seed, "SOURCE_NOTES", tmp_path / "missing-cathedral")

    db = data / "library.db"
    with connect(db) as conn:
        upsert_book(
            conn,
            Book(
                book_id=new_id("book"),
                title_en="if you're not first you're last",
                author="Grant Cardone",
                rights_basis=RightsBasis.PUBLIC_DOMAIN,
                source=BookSource.LOCAL_IMPORT,
                file_path=str(pdf),
                slug="Grant Cardone/if you're not first you're last",
            ),
        )

    attached = seed.attach_imported_cardone_pack(db_path=db)
    assert attached is not None
    assert attached.rights_basis is RightsBasis.LICENSED
    assert attached.title_en == "If You're Not First, You're Last"
    pack_dir = Path(attached.file_path).parent
    names = {path.name for path in pack_dir.iterdir()}
    assert "If-Youre-Not-First-Youre-Last.pdf" in names
    assert "01-introduction-en.txt" in names
    assert "03-mind-map.png" in names
    assert (pack_dir / "03-mind-map.png").read_bytes() == (src / "03-mind-map.png").read_bytes()
    assert "04-cover.png" in names
    with connect(db) as conn:
        kinds = {note.kind.value for note in notes_for(conn, attached.book_id)}
    assert kinds >= {"INTRO", "GUIDE", "MINDMAP", "COVER"}


def test_cardone_mindmap_artwork_is_valid() -> None:
    from PIL import Image

    from apple_lover_library.seed import SOURCE_CARDONE

    with Image.open(SOURCE_CARDONE / "03-mind-map.png") as image:
        assert image.format == "PNG"
        assert image.size == (1536, 1024)


def test_extract_pdf_cover_renders_first_page(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    from apple_lover_library.extract_cover import extract_pdf_cover

    pdf = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.write(pdf)
    dest = tmp_path / "cover.png"
    assert extract_pdf_cover(pdf, dest) is True
    assert dest.is_file()
    assert dest.stat().st_size > 0
