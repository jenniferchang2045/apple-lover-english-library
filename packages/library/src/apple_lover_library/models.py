from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from apple_lover_library.enums import BookSource, NoteKind, RightsBasis
from apple_lover_library.errors import RightsGateError


class Book(BaseModel):
    model_config = ConfigDict(extra="forbid")

    book_id: str
    title_en: str
    author: str
    title_zh: str = ""
    isbn: str | None = None
    edition: str | None = None
    language: str = "en"
    rights_basis: RightsBasis = RightsBasis.UNKNOWN
    source: BookSource = BookSource.MANUAL
    source_id: str | None = None
    file_path: str | None = None
    sha256: str | None = None
    slug: str = ""

    def can_download(self) -> bool:
        return self.rights_basis == RightsBasis.PUBLIC_DOMAIN

    def can_import_file(self) -> bool:
        return self.rights_basis in {RightsBasis.PUBLIC_DOMAIN, RightsBasis.LICENSED}


class CompanionNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str
    book_id: str
    title: str
    kind: NoteKind = NoteKind.OTHER
    file_path: str
    rights_basis: RightsBasis = RightsBasis.ORIGINAL


def require_downloadable(basis: RightsBasis) -> None:
    if basis != RightsBasis.PUBLIC_DOMAIN:
        raise RightsGateError("only PUBLIC_DOMAIN books may be downloaded from catalogs")


def require_importable(basis: RightsBasis) -> None:
    if basis not in {RightsBasis.PUBLIC_DOMAIN, RightsBasis.LICENSED}:
        raise RightsGateError("import requires PUBLIC_DOMAIN or LICENSED")
    if basis == RightsBasis.ORIGINAL:
        raise RightsGateError("ORIGINAL is for companion notes, not novel files")


class CatalogHit(BaseModel):
    source: str
    source_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    epub_url: str | None = None
    page_url: str | None = None
    borrow_url: str | None = None
    preview_url: str | None = None
    access: str = "catalog"
    can_download: bool = False
    score: float = 0.0
    gutenberg_id: int | None = None

    @property
    def author(self) -> str:
        return "; ".join(self.authors) if self.authors else "Unknown"

    @property
    def access_label(self) -> str:
        return {
            "public": "公版全文",
            "borrow": "可在线借阅",
            "preview": "可预览",
            "catalog": "仅书目",
        }.get(self.access, "仅书目")


GutenbergHit = CatalogHit
