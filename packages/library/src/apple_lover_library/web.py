from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from apple_lover_library.constants import APP_VERSION, DISPLAY_NAME
from apple_lover_library.download_public import download_gutenberg
from apple_lover_library.enums import RightsBasis
from apple_lover_library.errors import LibraryError, NotFoundError, RightsGateError
from apple_lover_library.import_local import import_local
from apple_lover_library.open_local import open_path
from apple_lover_library.search import search_catalogs
from apple_lover_library.seed import seed_companion_notes
from apple_lover_library.store import connect, get_book, get_note, list_books, notes_for

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))

app = FastAPI(title=DISPLAY_NAME)
seed_companion_notes()


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    q: str | None = None,
    author: str | None = None,
    ai: str | None = None,
) -> HTMLResponse:
    searched = bool((q or "").strip() or (author or "").strip())
    results = {
        "gutenberg": [],
        "openlibrary": [],
        "googlebooks": [],
        "archive": [],
        "google": [],
        "ai_candidates": [],
        "ai_enabled": False,
        "errors": {},
        "searched": searched,
        "phrase": "",
    }
    if searched:
        try:
            results.update(search_catalogs(q or "", author=author or "", use_ai=ai == "1"))
        except Exception as exc:  # noqa: BLE001
            results["errors"] = {"gutenberg": f"搜索出错：{exc.__class__.__name__}"}
    with connect() as conn:
        books = []
        for book in list_books(conn):
            books.append({"book": book, "notes": notes_for(conn, book.book_id)})
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "title": DISPLAY_NAME,
            "app_version": APP_VERSION,
            "books": books,
            "gutenberg": results["gutenberg"],
            "openlibrary": results["openlibrary"],
            "googlebooks": results.get("googlebooks") or [],
            "archive": results.get("archive") or [],
            "google": results["google"],
            "ai_candidates": results["ai_candidates"],
            "ai_enabled": results["ai_enabled"],
            "q": q or "",
            "author": author or "",
            "ai": ai == "1",
            "errors": results.get("errors") or {},
            "searched": results.get("searched", False),
            "phrase": results.get("phrase") or "",
        },
    )


@app.post("/import")
async def import_book(
    title: str = Form(...),
    author: str = Form(...),
    rights: str = Form(...),
    file: UploadFile = File(...),
) -> RedirectResponse:
    suffix = Path(file.filename or "book.epub").suffix.lower()
    if suffix not in {".epub", ".pdf"}:
        raise HTTPException(400, "only EPUB or PDF")
    tmp = Path.cwd() / "data" / f"upload{suffix}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(await file.read())
    try:
        import_local(tmp, title_en=title, author=author, rights_basis=RightsBasis(rights))
    except (RightsGateError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        tmp.unlink(missing_ok=True)
    return RedirectResponse("/", status_code=303)


@app.post("/download-gutenberg")
def download(gutenberg_id: int = Form(...)) -> RedirectResponse:
    try:
        download_gutenberg(gutenberg_id)
    except (LibraryError, RightsGateError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse("/", status_code=303)


@app.post("/open/book/{book_id}")
def open_book(book_id: str) -> RedirectResponse:
    try:
        with connect() as conn:
            book = get_book(conn, book_id)
        if not book.file_path:
            raise HTTPException(400, "no local file")
        open_path(book.file_path)
    except NotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return RedirectResponse("/", status_code=303)


@app.post("/open/note/{note_id}")
def open_note(note_id: str) -> RedirectResponse:
    try:
        with connect() as conn:
            note = get_note(conn, note_id)
        open_path(note.file_path)
    except NotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return RedirectResponse("/", status_code=303)
