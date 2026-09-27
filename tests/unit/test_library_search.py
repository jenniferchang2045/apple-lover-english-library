from __future__ import annotations

import httpx

from urllib.parse import unquote, unquote_plus

from apple_lover_library.search import (
    catalog_queries,
    fuzzy_score,
    google_books_query,
    google_discovery_links,
    remote_queries,
    search_archive_lending,
    search_gutenberg,
    search_google_books,
    search_open_library,
)


def test_fuzzy_author_and_title_need_not_be_complete() -> None:
    score = fuzzy_score(
        "Conversation in the Cathedral",
        ["Llosa, Mario Vargas"],
        query="cathedral",
        author_query="llosa",
    )
    assert score == 1.0
    partial = fuzzy_score("Pride and Prejudice", ["Austen, Jane"], query="prej", author_query="aust")
    assert partial == 1.0


def test_google_links_quote_title_and_author() -> None:
    links = google_discovery_links("If You're Not First, You're Last", "Grant Cardone")
    labels = {item["label"] for item in links}
    assert "Google · Project Gutenberg" in labels
    assert "Google Books" in labels
    assert "Amazon 购买" in labels
    exact = next(item for item in links if item["label"] == "Google 精确书目")
    decoded = unquote_plus(exact["url"])
    assert '"If You\'re Not First, You\'re Last"' in decoded
    assert '"Grant Cardone"' in decoded
    archive = next(item for item in links if item["label"] == "Internet Archive 借阅")
    assert "archive.org/search" in archive["url"]
    assert "site:archive.org" not in unquote_plus(archive["url"])
    joined = " ".join(item["url"] for item in links)
    assert "libgen" not in joined
    assert "annas-archive" not in joined
    assert "z-lib" not in joined
    assert all(
        "google.com/search" in item["url"]
        or "gutenberg.org" in item["url"]
        or "standardebooks.org" in item["url"]
        or "openlibrary.org" in item["url"]
        or "archive.org/search" in item["url"]
        or "amazon.com" in item["url"]
        or "bookshop.org" in item["url"]
        for item in links
    )


def test_catalog_queries_include_author_fragment() -> None:
    queries = catalog_queries("cathedral", "vargas")
    assert "cathedral vargas" in queries
    assert "vargas" in queries


def test_remote_queries_do_not_explode_into_every_token() -> None:
    assert remote_queries("", "Grant Cardone") == ["Grant Cardone"]
    variants = remote_queries("If You're Not First, You're Last", "Grant Cardone")
    assert variants[0] == "Grant Cardone"
    assert "not first last" in variants[1]


def test_stopwords_do_not_drown_title_score() -> None:
    score = fuzzy_score(
        "If You're Not First, You're Last",
        ["Cardone, Grant"],
        query="If You're Not First, You're Last",
        author_query="Grant Cardone",
    )
    assert score == 1.0


def test_google_books_query_uses_intitle_and_inauthor() -> None:
    q = google_books_query("If You're Not First, You're Last", "Grant Cardone")
    assert 'intitle:"If You\'re Not First, You\'re Last"' in q
    assert 'inauthor:"Grant Cardone"' in q


def test_homepage_renders_without_query() -> None:
    from fastapi.testclient import TestClient

    from apple_lover_library.web import app

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "apple_lover" in response.text


def test_failed_catalogs_still_return_google_links() -> None:
    from apple_lover_library.search import search_catalogs

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    results = search_catalogs(
        "",
        author="Grant Cardone",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert results["searched"] is True
    assert results["google"]
    assert results["gutenberg"] == []
    assert results["googlebooks"] == []
    assert results["archive"] == []
    assert results["errors"]


def test_gutenberg_results_include_author_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 54851,
                        "title": "Conversation in the Cathedral",
                        "authors": [{"name": "Llosa, Mario Vargas"}],
                        "languages": ["en"],
                        "formats": {},
                    }
                ]
            },
        )

    hits = search_gutenberg("cathedral", author="llosa", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert hits
    assert "Vargas" in hits[0].author
    assert hits[0].gutenberg_id == 54851


def test_open_library_uses_title_and_author_fields() -> None:
    seen: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(
            200,
            json={
                "docs": [
                    {
                        "key": "/works/OL123W",
                        "title": "If You're Not First, You're Last",
                        "author_name": ["Grant Cardone"],
                        "ebook_access": "borrowable",
                        "ia": ["ifyourenotfirstyourelast"],
                    },
                    {
                        "key": "/works/OL999W",
                        "title": "If You're Not First, You're Last",
                        "author_name": ["Grant Cardone"],
                        "ebook_access": "no_ebook",
                    },
                ]
            },
        )

    hits = search_open_library(
        "If You're Not First, You're Last",
        author="Grant Cardone",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert len(hits) == 1
    assert hits[0].title.startswith("If You're Not First")
    assert hits[0].access == "borrow"
    assert hits[0].borrow_url and "archive.org/details" in hits[0].borrow_url
    first = str(seen[0])
    assert "title=" in first and "author=" in first
    assert "language=eng" in first


def test_google_books_returns_bibliographic_hit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "intitle" in str(request.url)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "abc123",
                        "volumeInfo": {
                            "title": "If You're Not First, You're Last",
                            "authors": ["Grant Cardone"],
                            "language": "en",
                            "infoLink": "https://books.google.com/books?id=abc123",
                            "previewLink": "https://books.google.com/books?id=abc123&printsec=frontcover",
                        },
                        "accessInfo": {"viewability": "PARTIAL"},
                    }
                ]
            },
        )

    hits = search_google_books(
        "If You're Not First, You're Last",
        author="Grant Cardone",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert hits[0].source == "googlebooks"
    assert hits[0].can_download is False
    assert hits[0].access == "preview"
    assert hits[0].preview_url
    assert "books.google.com" in (hits[0].page_url or "")


def test_archive_lendable_is_borrow_not_download() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "response": {
                    "docs": [
                        {
                            "identifier": "ifyourenotfirstyourelast",
                            "title": "If You're Not First, You're Last",
                            "creator": ["Grant Cardone"],
                            "lending___is_lendable": "true",
                        }
                    ]
                }
            },
        )

    hits = search_archive_lending(
        "If You're Not First, You're Last",
        author="Grant Cardone",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert hits[0].access == "borrow"
    assert hits[0].can_download is False
    assert hits[0].borrow_url.endswith("/ifyourenotfirstyourelast")
