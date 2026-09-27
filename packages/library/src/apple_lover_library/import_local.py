from __future__ import annotations

import shutil
from pathlib import Path

from apple_lover_library.enums import BookSource, RightsBasis
from apple_lover_library.ids import new_id, safe_name, sha256_file
from apple_lover_library.models import Book, require_importable
from apple_lover_library.paths import LIBRARY_BOOKS, ensure_dirs
from apple_lover_library.store import connect, upsert_book


def import_local(
    source_file: Path,
    *,
    title_en: str,
    author: str,
    rights_basis: RightsBasis,
    title_zh: str = "",
    isbn: str | None = None,
    db_path: Path | None = None,
) -> Book:
    require_importable(rights_basis)
    path = Path(source_file).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if path.suffix.lower() not in {".epub", ".pdf"}:
        raise ValueError("only EPUB and PDF can be imported")

    ensure_dirs()
    slug = f"{safe_name(author)}/{safe_name(title_en)}"
    dest_dir = LIBRARY_BOOKS / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    shutil.copy2(path, dest)
    book = Book(
        book_id=new_id("book"),
        title_en=title_en,
        author=author,
        title_zh=title_zh,
        isbn=isbn,
        rights_basis=rights_basis,
        source=BookSource.LOCAL_IMPORT,
        file_path=str(dest),
        sha256=sha256_file(dest),
        slug=slug,
    )
    with connect(db_path) as conn:
        return upsert_book(conn, book)
