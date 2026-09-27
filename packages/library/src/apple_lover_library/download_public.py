from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from apple_lover_library.constants import (
    GUTENBERG_ALLOWED_HOSTS,
    GUTENDEX_URL,
    STANDARD_EBOOKS_HOST,
)
from apple_lover_library.enums import BookSource, RightsBasis
from apple_lover_library.errors import LibraryError, RightsGateError
from apple_lover_library.ids import new_id, safe_name, sha256_file
from apple_lover_library.models import Book, require_downloadable
from apple_lover_library.paths import LIBRARY_BOOKS, ensure_dirs
from apple_lover_library.store import connect, find_by_source, upsert_book


def download_gutenberg(gutenberg_id: int, *, client: httpx.Client | None = None, db_path: Path | None = None) -> Book:
    require_downloadable(RightsBasis.PUBLIC_DOMAIN)
    http = client or httpx.Client(timeout=60.0, follow_redirects=True)
    own = client is None
    try:
        with connect(db_path) as conn:
            existing = find_by_source(conn, BookSource.GUTENBERG, str(gutenberg_id))
            if existing and existing.file_path and Path(existing.file_path).is_file():
                return existing

        response = http.get(f"{GUTENDEX_URL}/{gutenberg_id}")
        response.raise_for_status()
        payload = response.json()
        authors = payload.get("authors") or []
        author = authors[0]["name"] if authors else "Unknown"
        title = payload.get("title") or f"Gutenberg {gutenberg_id}"
        formats = payload.get("formats") or {}
        epub_url = formats.get("application/epub+zip")
        if not epub_url:
            raise LibraryError("no EPUB on this Gutenberg record")
        _assert_gutenberg_url(epub_url)

        dest = _download_file(http, epub_url, author=author, title=title, filename=f"pg{gutenberg_id}.epub")
        book = Book(
            book_id=new_id("book"),
            title_en=title,
            author=author,
            rights_basis=RightsBasis.PUBLIC_DOMAIN,
            source=BookSource.GUTENBERG,
            source_id=str(gutenberg_id),
            file_path=str(dest),
            sha256=sha256_file(dest),
            slug=f"{safe_name(author)}/{safe_name(title)}",
        )
        with connect(db_path) as conn:
            existing = find_by_source(conn, BookSource.GUTENBERG, str(gutenberg_id))
            if existing:
                book = book.model_copy(update={"book_id": existing.book_id})
            return upsert_book(conn, book)
    finally:
        if own:
            http.close()


def download_standard_ebooks_epub(url: str, *, title_en: str, author: str, client: httpx.Client | None = None, db_path: Path | None = None) -> Book:
    require_downloadable(RightsBasis.PUBLIC_DOMAIN)
    parsed = urlparse(url)
    if parsed.hostname != STANDARD_EBOOKS_HOST or not url.endswith(".epub"):
        raise RightsGateError("only standardebooks.org EPUB URLs are allowed")
    http = client or httpx.Client(timeout=60.0, follow_redirects=True)
    own = client is None
    try:
        dest = _download_file(http, url, author=author, title=title_en, filename=Path(parsed.path).name)
        book = Book(
            book_id=new_id("book"),
            title_en=title_en,
            author=author,
            rights_basis=RightsBasis.PUBLIC_DOMAIN,
            source=BookSource.STANDARD_EBOOKS,
            source_id=url,
            file_path=str(dest),
            sha256=sha256_file(dest),
            slug=f"{safe_name(author)}/{safe_name(title_en)}",
        )
        with connect(db_path) as conn:
            return upsert_book(conn, book)
    finally:
        if own:
            http.close()


def _assert_gutenberg_url(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in GUTENBERG_ALLOWED_HOSTS:
        raise RightsGateError("download URL is not a Gutenberg host")


def _download_file(http: httpx.Client, url: str, *, author: str, title: str, filename: str) -> Path:
    ensure_dirs()
    dest_dir = LIBRARY_BOOKS / safe_name(author) / safe_name(title)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    with http.stream("GET", url) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
    return dest
