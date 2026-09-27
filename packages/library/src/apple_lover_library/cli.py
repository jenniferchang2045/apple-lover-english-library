from __future__ import annotations

import argparse
import sys

from apple_lover_library.constants import DISPLAY_NAME
from apple_lover_library.download_public import download_gutenberg
from apple_lover_library.search import search_catalogs
from apple_lover_library.enums import RightsBasis
from apple_lover_library.import_local import import_local
from apple_lover_library.open_local import open_path
from apple_lover_library.seed import seed_companion_notes
from apple_lover_library.store import connect, get_book, get_note, list_books, notes_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apple-lover-library", description=DISPLAY_NAME)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list books")
    search = sub.add_parser("search", help="fuzzy search Gutenberg, Open Library, Google Books, and discovery links")
    search.add_argument("query")
    search.add_argument("--author", default="")
    search.add_argument("--ai", action="store_true")
    dl = sub.add_parser("download-gutenberg", help="download a public-domain EPUB")
    dl.add_argument("gutenberg_id", type=int)
    imp = sub.add_parser("import", help="import a local EPUB/PDF you already own")
    imp.add_argument("path")
    imp.add_argument("--title", required=True)
    imp.add_argument("--author", required=True)
    imp.add_argument("--rights", choices=["PUBLIC_DOMAIN", "LICENSED"], required=True)
    open_p = sub.add_parser("open", help="open a book file")
    open_p.add_argument("book_id")
    notes = sub.add_parser("notes", help="list or open notes")
    notes.add_argument("book_id")
    notes.add_argument("--open", dest="note_id")
    sub.add_parser("serve", help="start the local catalog at http://127.0.0.1:8765")
    sub.add_parser("seed", help="load companion notes for Conversation in the Cathedral")

    args = parser.parse_args(argv)
    seed_companion_notes()

    if args.cmd == "list":
        with connect() as conn:
            for book in list_books(conn):
                mark = "file" if book.file_path else "no-file"
                print(f"{book.book_id}\t{book.author}\t{book.title_en}\t{book.rights_basis}\t{mark}")
        return 0
    if args.cmd == "search":
        results = search_catalogs(args.query, author=args.author, use_ai=args.ai)
        for hit in results["gutenberg"]:
            print(f"gutenberg\t{hit.author}\t{hit.title}\t{hit.gutenberg_id}\t{hit.score:.2f}")
        for hit in results["openlibrary"]:
            print(f"openlibrary\t{hit.author}\t{hit.title}\t{hit.gutenberg_id or '-'}\t{hit.score:.2f}")
        for hit in results.get("googlebooks") or []:
            print(f"googlebooks\t{hit.author}\t{hit.title}\t{hit.access}\t{hit.score:.2f}")
        for hit in results.get("archive") or []:
            print(f"archive\t{hit.author}\t{hit.title}\t{hit.access}\t{hit.score:.2f}")
        for link in results["google"]:
            print(f"link\t{link['label']}\t{link['url']}")
        return 0
    if args.cmd == "download-gutenberg":
        book = download_gutenberg(args.gutenberg_id)
        print(f"saved {book.book_id} -> {book.file_path}")
        return 0
    if args.cmd == "import":
        book = import_local(
            args.path,
            title_en=args.title,
            author=args.author,
            rights_basis=RightsBasis(args.rights),
        )
        print(f"imported {book.book_id} -> {book.file_path}")
        return 0
    if args.cmd == "open":
        with connect() as conn:
            book = get_book(conn, args.book_id)
        if not book.file_path:
            print("no local file for this book", file=sys.stderr)
            return 2
        open_path(book.file_path)
        return 0
    if args.cmd == "notes":
        with connect() as conn:
            if args.note_id:
                open_path(get_note(conn, args.note_id).file_path)
                return 0
            for note in notes_for(conn, args.book_id):
                print(f"{note.note_id}\t{note.kind}\t{note.title}\t{note.file_path}")
        return 0
    if args.cmd == "seed":
        book = seed_companion_notes()
        print(f"seeded {book.book_id if book else 'nothing'}")
        return 0
    if args.cmd == "serve":
        import uvicorn

        from apple_lover_library.web import app

        uvicorn.run(
            "apple_lover_library.web:app",
            host="127.0.0.1",
            port=8765,
            reload=True,
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
