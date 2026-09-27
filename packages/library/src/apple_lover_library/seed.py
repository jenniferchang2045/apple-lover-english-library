from __future__ import annotations

import shutil
from pathlib import Path

from apple_lover_library.enums import BookSource, NoteKind, RightsBasis
from apple_lover_library.extract_cover import extract_pdf_cover
from apple_lover_library.ids import new_id, safe_name
from apple_lover_library.models import Book, CompanionNote
from apple_lover_library.paths import LIBRARY_NOTES, ROOT, ensure_dirs
from apple_lover_library.store import add_note, connect, list_books, notes_for, upsert_book

CATHEDRAL_SLUG = "mario-vargas-llosa/conversation-in-the-cathedral"
SOURCE_NOTES = ROOT / "content" / "packages" / "conversation-in-the-cathedral"
SOURCE_CARDONE = ROOT / "content" / "packages" / "if-youre-not-first-youre-last"
CARDONE_TITLE = "If You're Not First, You're Last"
CARDONE_PDF_NAME = "If-Youre-Not-First-Youre-Last.pdf"
CARDONE_PACK = [
    ("01-introduction-en.txt", "Original introduction", NoteKind.INTRO),
    ("02-reading-guide-en.txt", "Original reading guide", NoteKind.GUIDE),
    ("03-mind-map.png", "Original mind map", NoteKind.MINDMAP),
    ("04-cover.png", "Book cover", NoteKind.COVER),
]


def seed_companion_notes(db_path: Path | None = None) -> Book | None:
    """Seed Cathedral notes, then attach any imported Cardone study pack beside its PDF."""
    ensure_dirs()
    cathedral = _seed_cathedral(db_path)
    attach_imported_cardone_pack(db_path)
    return cathedral


def _seed_cathedral(db_path: Path | None = None) -> Book | None:
    """Catalog Cathedral as UNKNOWN with original notes, without copying the novel PDF."""
    with connect(db_path) as conn:
        for book in list_books(conn):
            if book.slug == CATHEDRAL_SLUG:
                return book

        book = Book(
            book_id=new_id("book"),
            title_en="Conversation in the Cathedral",
            title_zh="酒吧长谈",
            author="Mario Vargas Llosa",
            language="en",
            rights_basis=RightsBasis.UNKNOWN,
            source=BookSource.MANUAL,
            file_path=None,
            slug=CATHEDRAL_SLUG,
        )
        upsert_book(conn, book)

        dest = LIBRARY_NOTES / safe_name(CATHEDRAL_SLUG.replace("/", "_"))
        dest.mkdir(parents=True, exist_ok=True)
        mapping = [
            ("01-introduction-en.txt", "Original introduction", NoteKind.INTRO),
            ("02-reading-guide-en.txt", "Original reading guide", NoteKind.GUIDE),
        ]
        for name, title, kind in mapping:
            src = SOURCE_NOTES / name
            if not src.is_file():
                continue
            target = dest / name
            shutil.copy2(src, target)
            add_note(
                conn,
                CompanionNote(
                    note_id=new_id("note"),
                    book_id=book.book_id,
                    title=title,
                    kind=kind,
                    file_path=str(target),
                ),
            )

        mind = None
        for candidate in ("03-mind-map.png", "03-mind map.png"):
            if (SOURCE_NOTES / candidate).is_file():
                mind = SOURCE_NOTES / candidate
                break
        if mind is not None:
            target = dest / "03-mind-map.png"
            shutil.copy2(mind, target)
            add_note(
                conn,
                CompanionNote(
                    note_id=new_id("note"),
                    book_id=book.book_id,
                    title="Original mind map",
                    kind=NoteKind.MINDMAP,
                    file_path=str(target),
                ),
            )
        return book


def attach_imported_cardone_pack(db_path: Path | None = None) -> Book | None:
    """Put original notes beside the imported PDF, extract its cover, and mark it LICENSED."""
    if not SOURCE_CARDONE.is_dir():
        return None
    with connect(db_path) as conn:
        book = next((item for item in list_books(conn) if _is_cardone_import(item)), None)
        if book is None or not book.file_path:
            return None
        folder = Path(book.file_path).parent
        folder.mkdir(parents=True, exist_ok=True)
        pdf = Path(book.file_path)
        dest_pdf = folder / CARDONE_PDF_NAME
        if pdf.is_file() and pdf.resolve() != dest_pdf.resolve():
            if dest_pdf.exists():
                dest_pdf.unlink()
            pdf.replace(dest_pdf)
            book.file_path = str(dest_pdf)
        book.title_en = CARDONE_TITLE
        book.rights_basis = RightsBasis.LICENSED
        upsert_book(conn, book)

        existing_kinds = {note.kind for note in notes_for(conn, book.book_id)}
        for name, title, kind in CARDONE_PACK:
            src = SOURCE_CARDONE / name
            if not src.is_file():
                continue
            target = folder / name
            shutil.copy2(src, target)
            if kind in existing_kinds:
                continue
            add_note(
                conn,
                CompanionNote(
                    note_id=new_id("note"),
                    book_id=book.book_id,
                    title=title,
                    kind=kind,
                    file_path=str(target),
                ),
            )
        readme = SOURCE_CARDONE / "README.md"
        if readme.is_file():
            shutil.copy2(readme, folder / "README.md")
        cover = folder / "04-cover.png"
        pdf_now = Path(book.file_path)
        if extract_pdf_cover(pdf_now, cover):
            _keep_single_cover_note(conn, book.book_id, cover)
        return book


def _keep_single_cover_note(conn, book_id: str, file_path: Path) -> None:
    covers = [note for note in notes_for(conn, book_id) if note.kind is NoteKind.COVER]
    if not covers:
        return
    keep = covers[0]
    conn.execute(
        "UPDATE notes SET title = ?, file_path = ? WHERE note_id = ?",
        ("Book cover", str(file_path), keep.note_id),
    )
    for extra in covers[1:]:
        conn.execute("DELETE FROM notes WHERE note_id = ?", (extra.note_id,))
    conn.commit()


def _is_cardone_import(book: Book) -> bool:
    return "cardone" in book.author.lower() and bool(book.file_path)
