from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from apple_lover_library.download_public import download_gutenberg
from apple_lover_library.search import search_gutenberg
from apple_lover_library.enums import BookSource, RightsBasis


def test_search_and_download_gutenberg_mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import apple_lover_library.download_public as dl
    import apple_lover_library.paths as paths

    books = tmp_path / "books"
    data = tmp_path / "data"
    monkeypatch.setattr(paths, "LIBRARY_BOOKS", books)
    monkeypatch.setattr(paths, "DATA_DIR", data)
    monkeypatch.setattr(paths, "DB_PATH", data / "library.db")
    monkeypatch.setattr(dl, "LIBRARY_BOOKS", books)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/books") and "search" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": 1342,
                            "title": "Pride and Prejudice",
                            "authors": [{"name": "Austen, Jane"}],
                            "languages": ["en"],
                            "formats": {"application/epub+zip": "https://www.gutenberg.org/ebooks/1342.epub.images"},
                        }
                    ]
                },
            )
        if request.url.path.endswith("/books/1342"):
            return httpx.Response(
                200,
                json={
                    "id": 1342,
                    "title": "Pride and Prejudice",
                    "authors": [{"name": "Austen, Jane"}],
                    "formats": {"application/epub+zip": "https://www.gutenberg.org/ebooks/1342.epub.images"},
                },
            )
        if "gutenberg.org" in request.url.host:
            return httpx.Response(200, content=b"PK\x03\x04epub")
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    hits = search_gutenberg("pride", client=client)
    assert hits[0].gutenberg_id == 1342
    book = download_gutenberg(1342, client=client, db_path=data / "library.db")
    assert book.rights_basis is RightsBasis.PUBLIC_DOMAIN
    assert book.source is BookSource.GUTENBERG
    assert Path(book.file_path or "").is_file()
