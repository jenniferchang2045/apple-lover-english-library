from __future__ import annotations

import json
import os
import re
from urllib.parse import quote_plus

import httpx

from apple_lover_library.constants import (
    ARCHIVE_SEARCH_URL,
    GOOGLE_BOOKS_URL,
    GUTENDEX_URL,
    OPEN_LIBRARY_URL,
)
from apple_lover_library.models import CatalogHit

_TOKEN = re.compile(r"[a-z0-9\u4e00-\u9fff]{2,}", re.I)
_STOP = {
    "if",
    "you",
    "re",
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "is",
    "are",
    "for",
    "on",
    "at",
    "by",
}
_CONTRACTIONS = {
    "you're": "you are",
    "i'm": "i am",
    "don't": "do not",
    "can't": "cannot",
    "it's": "it is",
    "that's": "that is",
    "won't": "will not",
}


def expand_contractions(text: str) -> str:
    out = text or ""
    for raw, full in _CONTRACTIONS.items():
        out = re.sub(re.escape(raw), full, out, flags=re.I)
    return out


def tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN.finditer(expand_contractions(text or ""))]


def significant_tokens(text: str) -> list[str]:
    return [tok for tok in tokens(text) if tok not in _STOP]


def fuzzy_score(title: str, authors: list[str], *, query: str, author_query: str = "") -> float:
    """Partial match. Stopwords do not dominate the score."""
    hay = tokens(title) + [t for name in authors for t in tokens(name)]
    needles = significant_tokens(query) + significant_tokens(author_query)
    if not needles:
        needles = tokens(query) + tokens(author_query)
    if not needles:
        return 0.0
    hits = 0
    for needle in needles:
        if any(needle == piece or needle in piece or piece in needle for piece in hay):
            hits += 1
    return hits / len(needles)


def author_matches(authors: list[str], author_query: str) -> bool:
    if not author_query.strip():
        return True
    return fuzzy_score("", authors, query="", author_query=author_query) >= 0.5


def catalog_queries(title_or_query: str, author: str = "") -> list[str]:
    parts = [title_or_query.strip(), author.strip()]
    combined = " ".join(p for p in parts if p)
    seen: list[str] = []
    for item in (combined, title_or_query.strip(), author.strip(), *tokens(combined)):
        if item and item not in seen and len(item) >= 2:
            seen.append(item)
    return seen[:6]


def remote_queries(title_or_query: str, author: str = "") -> list[str]:
    title = title_or_query.strip()
    name = author.strip()
    sig = " ".join(significant_tokens(title))
    seen: list[str] = []
    for item in (name, " ".join(p for p in (sig, name) if p), title):
        if item and item not in seen:
            seen.append(item)
    return seen[:2]


def quoted_phrase(title: str, author: str) -> str:
    title = title.strip()
    author = author.strip()
    if title and author:
        return f'"{title}" "{author}"'
    if title:
        return f'"{title}"'
    return f'"{author}"' if author else ""


def google_discovery_links(title_or_query: str, author: str = "") -> list[dict[str, str]]:
    title = title_or_query.strip()
    name = author.strip()
    phrase = quoted_phrase(title, name)
    if not phrase:
        return []
    encoded = quote_plus(phrase)
    title_q = quote_plus(title) if title else encoded
    author_q = quote_plus(name) if name else ""
    archive_q = quote_plus(
        " AND ".join(
            p
            for p in (
                f'title:"{title}"' if title else "",
                f'creator:"{name}"' if name else "",
                "mediatype:texts",
            )
            if p
        )
    )
    links = [
        {"label": "Google 精确书目", "url": f"https://www.google.com/search?q={encoded}"},
        {"label": "Google Books", "url": f"https://www.google.com/search?q={encoded}&tbm=bks"},
        {
            "label": "Open Library 站内",
            "url": f"https://openlibrary.org/search?q={title_q}"
            + (f"&author={author_q}" if author_q else ""),
        },
        {
            "label": "Google · Project Gutenberg",
            "url": f"https://www.google.com/search?q={encoded}+site%3Agutenberg.org",
        },
        {
            "label": "Google · Standard Ebooks",
            "url": f"https://www.google.com/search?q={encoded}+site%3Astandardebooks.org",
        },
        {
            "label": "Google · Open Library",
            "url": f"https://www.google.com/search?q={encoded}+site%3Aopenlibrary.org",
        },
        {
            "label": "Internet Archive 借阅",
            "url": f"https://archive.org/search?query={archive_q}",
        },
        {
            "label": "Amazon 购买",
            "url": f"https://www.amazon.com/s?k={quote_plus(' '.join(p for p in (title, name) if p))}",
        },
        {
            "label": "Bookshop 购买",
            "url": f"https://bookshop.org/search?keywords={quote_plus(' '.join(p for p in (title, name) if p))}",
        },
    ]
    return links


def expand_with_ai(title_or_query: str, author: str = "") -> list[dict[str, str]]:
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        return []
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    prompt = (
        "User is identifying an English book in legal catalogs. "
        "Return JSON {\"candidates\":[{\"title\":\"...\",\"author\":\"...\"}]} "
        "with up to 5 bibliographic matches. Do not suggest pirate or file-host sites."
    )
    user = f"title/query: {title_or_query}\nauthor fragment: {author}"
    try:
        response = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user},
                ],
            },
            timeout=20.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        start = content.find("{")
        end = content.rfind("}")
        payload = json.loads(content[start : end + 1])
        out = []
        for item in payload.get("candidates") or []:
            title = str(item.get("title") or "").strip()
            name = str(item.get("author") or "").strip()
            if title or name:
                out.append({"title": title, "author": name})
        return out[:5]
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError):
        return []


def search_gutenberg(
    query: str,
    *,
    author: str = "",
    client: httpx.Client | None = None,
) -> list[CatalogHit]:
    http = client or httpx.Client(timeout=10.0, follow_redirects=True)
    own = client is None
    merged: dict[int, CatalogHit] = {}
    last_timeout: httpx.TimeoutException | None = None
    try:
        for q in remote_queries(query, author):
            try:
                response = http.get(GUTENDEX_URL, params={"search": q})
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                last_timeout = exc
                continue
            for item in response.json().get("results", []):
                gid = int(item["id"])
                names = [a.get("name") or "" for a in (item.get("authors") or []) if a.get("name")]
                title = item.get("title") or "Untitled"
                if not author_matches(names, author):
                    continue
                score = fuzzy_score(title, names, query=query, author_query=author)
                formats = item.get("formats") or {}
                epub = formats.get("application/epub+zip")
                hit = CatalogHit(
                    source="gutenberg",
                    source_id=str(gid),
                    gutenberg_id=gid,
                    title=title,
                    authors=names or ["Unknown"],
                    languages=item.get("languages") or [],
                    epub_url=epub,
                    page_url=f"https://www.gutenberg.org/ebooks/{gid}",
                    can_download=bool(epub),
                    score=score,
                )
                prev = merged.get(gid)
                if prev is None or hit.score > prev.score:
                    merged[gid] = hit
        hits = [h for h in merged.values() if h.score > 0 or not (tokens(query) or tokens(author))]
        hits.sort(key=lambda h: (-h.score, h.author, h.title))
        if not hits and last_timeout is not None:
            raise last_timeout
        return hits[:40]
    finally:
        if own:
            http.close()


def _open_library_strategies(query: str, author: str) -> list[dict[str, str | int]]:
    title = query.strip()
    name = author.strip()
    sig = " ".join(significant_tokens(title))
    strategies: list[dict[str, str | int]] = []
    if title and name:
        strategies.append({"title": title, "author": name, "limit": 12, "language": "eng"})
    if name:
        strategies.append({"author": name, "limit": 12, "language": "eng"})
    elif sig:
        strategies.append({"title": sig, "limit": 12, "language": "eng"})
    elif title:
        strategies.append({"q": title, "limit": 12, "language": "eng"})
    return strategies[:2]


def _collect_open_library_docs(
    docs: list[dict],
    query: str,
    author: str,
    merged: dict[str, CatalogHit],
) -> None:
    for item in docs:
        title = item.get("title") or "Untitled"
        names = list(item.get("author_name") or ["Unknown"])
        if not author_matches(names, author):
            continue
        score = fuzzy_score(title, names, query=query, author_query=author)
        if score < 0.34 and author.strip():
            continue
        key = item.get("key") or title
        gids = item.get("id_project_gutenberg") or []
        gid = int(gids[0]) if gids else None
        access, borrow_url = _open_library_access(item)
        hit = CatalogHit(
            source="openlibrary",
            source_id=str(key),
            gutenberg_id=gid,
            title=title,
            authors=names,
            languages=item.get("language") or [],
            page_url=f"https://openlibrary.org{key}" if str(key).startswith("/") else None,
            borrow_url=borrow_url,
            access=access,
            can_download=gid is not None,
            score=score,
        )
        prev = merged.get(hit.source_id)
        if prev is None or hit.score > prev.score:
            merged[hit.source_id] = hit


def search_open_library(
    query: str,
    *,
    author: str = "",
    client: httpx.Client | None = None,
) -> list[CatalogHit]:
    if not query.strip() and not author.strip():
        return []
    http = client or httpx.Client(timeout=10.0, follow_redirects=True)
    own = client is None
    merged: dict[str, CatalogHit] = {}
    try:
        for index, params in enumerate(_open_library_strategies(query, author)):
            if index and any(hit.score >= 0.6 for hit in merged.values()):
                break
            response = http.get(OPEN_LIBRARY_URL, params=params)
            response.raise_for_status()
            _collect_open_library_docs(response.json().get("docs") or [], query, author, merged)
        hits = _dedupe_title_author(list(merged.values()))
        hits.sort(key=lambda h: (_access_rank(h), -h.score, _language_rank(h), h.author, h.title))
        return hits[:12]
    finally:
        if own:
            http.close()


def google_books_query(title: str, author: str) -> str:
    title = title.strip()
    author = author.strip()
    parts: list[str] = []
    if title:
        parts.append(f'intitle:"{title}"')
    if author:
        parts.append(f'inauthor:"{author}"')
    return " ".join(parts) or title or author


def search_google_books(
    query: str,
    *,
    author: str = "",
    client: httpx.Client | None = None,
) -> list[CatalogHit]:
    q = google_books_query(query, author)
    if not q:
        return []
    http = client or httpx.Client(timeout=10.0, follow_redirects=True)
    own = client is None
    try:
        response = http.get(
            GOOGLE_BOOKS_URL,
            params={"q": q, "maxResults": 10, "printType": "books", "langRestrict": "en"},
        )
        response.raise_for_status()
        hits: list[CatalogHit] = []
        for item in response.json().get("items") or []:
            info = item.get("volumeInfo") or {}
            title = info.get("title") or "Untitled"
            names = list(info.get("authors") or ["Unknown"])
            if not author_matches(names, author):
                continue
            score = fuzzy_score(title, names, query=query, author_query=author)
            if score < 0.34 and (query.strip() or author.strip()):
                continue
            page = info.get("infoLink") or info.get("canonicalVolumeLink")
            preview = info.get("previewLink") or (item.get("accessInfo") or {}).get("webReaderLink")
            access = _google_books_access(item)
            hits.append(
                CatalogHit(
                    source="googlebooks",
                    source_id=str(item.get("id") or title),
                    title=title,
                    authors=names,
                    languages=[info["language"]] if info.get("language") else [],
                    page_url=page,
                    preview_url=preview if access == "preview" else None,
                    access=access,
                    can_download=False,
                    score=score,
                )
            )
        hits.sort(key=lambda h: (_access_rank(h), -h.score, _language_rank(h), h.author, h.title))
        return hits[:10]
    finally:
        if own:
            http.close()


def search_archive_lending(
    query: str,
    *,
    author: str = "",
    client: httpx.Client | None = None,
) -> list[CatalogHit]:
    title = query.strip()
    name = author.strip()
    clauses = ["mediatype:texts"]
    if title:
        clauses.append(f'title:"{title}"')
    if name:
        clauses.append(f'creator:"{name}"')
    if len(clauses) < 2:
        return []
    http = client or httpx.Client(timeout=10.0, follow_redirects=True)
    own = client is None
    try:
        response = http.get(
            ARCHIVE_SEARCH_URL,
            params={
                "q": " AND ".join(clauses),
                "fl[]": ["identifier", "title", "creator", "lending___is_lendable", "year"],
                "rows": 8,
                "page": 1,
                "output": "json",
            },
        )
        response.raise_for_status()
        docs = ((response.json().get("response") or {}).get("docs")) or []
        hits: list[CatalogHit] = []
        for item in docs:
            title_hit = item.get("title") or "Untitled"
            raw_creators = item.get("creator") or []
            names = raw_creators if isinstance(raw_creators, list) else [str(raw_creators)]
            if not author_matches(names, author):
                continue
            score = fuzzy_score(title_hit, names, query=query, author_query=author)
            if score < 0.34:
                continue
            identifier = str(item.get("identifier") or "").strip()
            if not identifier:
                continue
            lendable = str(item.get("lending___is_lendable") or "").lower() in {"true", "1"}
            page = f"https://archive.org/details/{identifier}"
            hits.append(
                CatalogHit(
                    source="archive",
                    source_id=identifier,
                    title=title_hit,
                    authors=names or ["Unknown"],
                    page_url=page,
                    borrow_url=page if lendable else None,
                    access="borrow" if lendable else "catalog",
                    can_download=False,
                    score=score,
                )
            )
        hits.sort(key=lambda h: (_access_rank(h), -h.score, h.author, h.title))
        return hits[:8]
    finally:
        if own:
            http.close()


def search_catalogs(
    query: str,
    *,
    author: str = "",
    use_ai: bool = False,
    client: httpx.Client | None = None,
) -> dict:
    from concurrent.futures import ThreadPoolExecutor

    extras = expand_with_ai(query, author) if use_ai else []
    errors: dict[str, str] = {}
    gutenberg: list[CatalogHit] = []
    openlib: list[CatalogHit] = []
    books: list[CatalogHit] = []
    archive: list[CatalogHit] = []

    def _gutenberg() -> list[CatalogHit]:
        return search_gutenberg(query, author=author, client=client)

    def _openlibrary() -> list[CatalogHit]:
        return search_open_library(query, author=author, client=client)

    def _google_books() -> list[CatalogHit]:
        return search_google_books(query, author=author, client=client)

    def _archive() -> list[CatalogHit]:
        return search_archive_lending(query, author=author, client=client)

    with ThreadPoolExecutor(max_workers=4) as pool:
        g_future = pool.submit(_gutenberg)
        o_future = pool.submit(_openlibrary)
        b_future = pool.submit(_google_books)
        a_future = pool.submit(_archive)
        try:
            gutenberg = g_future.result()
        except (httpx.HTTPError, TimeoutError, OSError) as exc:
            errors["gutenberg"] = _catalog_error("Gutenberg", exc)
        try:
            openlib = o_future.result()
        except (httpx.HTTPError, TimeoutError, OSError) as exc:
            errors["openlibrary"] = _catalog_error("Open Library", exc)
        try:
            books = b_future.result()
        except (httpx.HTTPError, TimeoutError, OSError) as exc:
            errors["googlebooks"] = _catalog_error("Google Books", exc)
        try:
            archive = a_future.result()
        except (httpx.HTTPError, TimeoutError, OSError) as exc:
            errors["archive"] = _catalog_error("Internet Archive", exc)

    for extra in extras:
        extra_title = extra.get("title") or query
        extra_author = extra.get("author") or author
        try:
            gutenberg = _merge_hits(
                gutenberg,
                search_gutenberg(extra_title, author=extra_author, client=client),
            )
        except (httpx.HTTPError, TimeoutError, OSError):
            pass
        try:
            openlib = _merge_hits(
                openlib,
                search_open_library(extra_title, author=extra_author, client=client),
            )
        except (httpx.HTTPError, TimeoutError, OSError):
            pass
        try:
            books = _merge_hits(
                books,
                search_google_books(extra_title, author=extra_author, client=client),
            )
        except (httpx.HTTPError, TimeoutError, OSError):
            pass
        try:
            archive = _merge_hits(
                archive,
                search_archive_lending(extra_title, author=extra_author, client=client),
            )
        except (httpx.HTTPError, TimeoutError, OSError):
            pass

    return {
        "gutenberg": gutenberg,
        "openlibrary": openlib,
        "googlebooks": books,
        "archive": archive,
        "google": google_discovery_links(query, author),
        "ai_candidates": extras,
        "ai_enabled": bool(os.environ.get("LLM_API_KEY", "").strip()),
        "errors": errors,
        "searched": True,
        "phrase": quoted_phrase(query, author),
    }


def _open_library_access(item: dict) -> tuple[str, str | None]:
    ebook = str(item.get("ebook_access") or "").lower()
    ia_ids = item.get("ia") or []
    identifier = str(ia_ids[0]) if ia_ids else ""
    borrow = f"https://archive.org/details/{identifier}" if identifier else None
    if ebook == "public":
        return "public", borrow
    if ebook == "borrowable":
        return "borrow", borrow
    return "catalog", None


def _google_books_access(item: dict) -> str:
    view = str((item.get("accessInfo") or {}).get("viewability") or "").upper()
    if view in {"PARTIAL", "ALL_PAGES", "FULL_PUBLIC_DOMAIN"}:
        return "preview"
    return "catalog"


def _access_rank(hit: CatalogHit) -> int:
    return {"public": 0, "borrow": 1, "preview": 2, "catalog": 3}.get(hit.access, 3)


def _dedupe_title_author(hits: list[CatalogHit]) -> list[CatalogHit]:
    best: dict[tuple[str, str], CatalogHit] = {}
    for hit in hits:
        key = (" ".join(significant_tokens(hit.title)), hit.author.lower())
        prev = best.get(key)
        if prev is None:
            best[key] = hit
            continue
        better_access = _access_rank(hit) < _access_rank(prev)
        same_access_better_score = _access_rank(hit) == _access_rank(prev) and hit.score > prev.score
        if better_access or same_access_better_score:
            best[key] = hit
    return list(best.values())


def _language_rank(hit: CatalogHit) -> int:
    langs = [str(x).lower() for x in hit.languages]
    if not langs or any(x.startswith("en") or x == "eng" for x in langs):
        return 0
    return 1


def _catalog_error(name: str, exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return f"{name} 暂时限流，请用上面的精确外链。"
    if isinstance(exc, httpx.TimeoutException):
        return f"{name} 超时。请确认本机网络能打开对应站点。"
    return f"{name} 请求失败：{exc.__class__.__name__}"


def _merge_hits(left: list[CatalogHit], right: list[CatalogHit]) -> list[CatalogHit]:
    by_key = {(h.source, h.source_id): h for h in left}
    for hit in right:
        key = (hit.source, hit.source_id)
        prev = by_key.get(key)
        if prev is None or hit.score > prev.score:
            by_key[key] = hit
    hits = list(by_key.values())
    hits.sort(key=lambda h: (-h.score, h.author, h.title))
    return hits[:40]
