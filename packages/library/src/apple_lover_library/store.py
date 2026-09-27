from __future__ import annotations

import sqlite3
from pathlib import Path

from apple_lover_library.enums import BookSource, NoteKind, RightsBasis
from apple_lover_library.errors import NotFoundError
from apple_lover_library.models import Book, CompanionNote
from apple_lover_library.paths import DB_PATH, ensure_dirs


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    ensure_dirs()
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            book_id TEXT PRIMARY KEY,
            title_en TEXT NOT NULL,
            author TEXT NOT NULL,
            title_zh TEXT NOT NULL DEFAULT '',
            isbn TEXT,
            edition TEXT,
            language TEXT NOT NULL DEFAULT 'en',
            rights_basis TEXT NOT NULL,
            source TEXT NOT NULL,
            source_id TEXT,
            file_path TEXT,
            sha256 TEXT,
            slug TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notes (
            note_id TEXT PRIMARY KEY,
            book_id TEXT NOT NULL,
            title TEXT NOT NULL,
            kind TEXT NOT NULL,
            file_path TEXT NOT NULL,
            rights_basis TEXT NOT NULL DEFAULT 'ORIGINAL',
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        );
        """
    )
    conn.commit()


def upsert_book(conn: sqlite3.Connection, book: Book) -> Book:
    conn.execute(
        """
        INSERT INTO books (
            book_id, title_en, author, title_zh, isbn, edition, language,
            rights_basis, source, source_id, file_path, sha256, slug
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(book_id) DO UPDATE SET
            title_en=excluded.title_en,
            author=excluded.author,
            title_zh=excluded.title_zh,
            isbn=excluded.isbn,
            edition=excluded.edition,
            language=excluded.language,
            rights_basis=excluded.rights_basis,
            source=excluded.source,
            source_id=excluded.source_id,
            file_path=excluded.file_path,
            sha256=excluded.sha256,
            slug=excluded.slug
        """,
        (
            book.book_id,
            book.title_en,
            book.author,
            book.title_zh,
            book.isbn,
            book.edition,
            book.language,
            book.rights_basis.value,
            book.source.value,
            book.source_id,
            book.file_path,
            book.sha256,
            book.slug,
        ),
    )
    conn.commit()
    return book


def add_note(conn: sqlite3.Connection, note: CompanionNote) -> CompanionNote:
    conn.execute(
        """
        INSERT OR REPLACE INTO notes (note_id, book_id, title, kind, file_path, rights_basis)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            note.note_id,
            note.book_id,
            note.title,
            note.kind.value,
            note.file_path,
            note.rights_basis.value,
        ),
    )
    conn.commit()
    return note


def list_books(conn: sqlite3.Connection) -> list[Book]:
    rows = conn.execute("SELECT * FROM books ORDER BY author, title_en").fetchall()
    return [_book(row) for row in rows]


def get_book(conn: sqlite3.Connection, book_id: str) -> Book:
    row = conn.execute("SELECT * FROM books WHERE book_id = ?", (book_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"book not found: {book_id}")
    return _book(row)


def notes_for(conn: sqlite3.Connection, book_id: str) -> list[CompanionNote]:
    rows = conn.execute(
        "SELECT * FROM notes WHERE book_id = ? ORDER BY kind, title", (book_id,)
    ).fetchall()
    return [_note(row) for row in rows]


def get_note(conn: sqlite3.Connection, note_id: str) -> CompanionNote:
    row = conn.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"note not found: {note_id}")
    return _note(row)


def find_by_source(conn: sqlite3.Connection, source: BookSource, source_id: str) -> Book | None:
    row = conn.execute(
        "SELECT * FROM books WHERE source = ? AND source_id = ?",
        (source.value, source_id),
    ).fetchone()
    return _book(row) if row else None


def _book(row: sqlite3.Row) -> Book:
    return Book(
        book_id=row["book_id"],
        title_en=row["title_en"],
        author=row["author"],
        title_zh=row["title_zh"],
        isbn=row["isbn"],
        edition=row["edition"],
        language=row["language"],
        rights_basis=RightsBasis(row["rights_basis"]),
        source=BookSource(row["source"]),
        source_id=row["source_id"],
        file_path=row["file_path"],
        sha256=row["sha256"],
        slug=row["slug"],
    )


def _note(row: sqlite3.Row) -> CompanionNote:
    return CompanionNote(
        note_id=row["note_id"],
        book_id=row["book_id"],
        title=row["title"],
        kind=NoteKind(row["kind"]),
        file_path=row["file_path"],
        rights_basis=RightsBasis(row["rights_basis"]),
    )
