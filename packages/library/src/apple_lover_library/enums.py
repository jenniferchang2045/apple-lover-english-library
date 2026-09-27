from __future__ import annotations

from enum import StrEnum


class RightsBasis(StrEnum):
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    LICENSED = "LICENSED"
    ORIGINAL = "ORIGINAL"
    UNKNOWN = "UNKNOWN"


class BookSource(StrEnum):
    MANUAL = "MANUAL"
    LOCAL_IMPORT = "LOCAL_IMPORT"
    GUTENBERG = "GUTENBERG"
    STANDARD_EBOOKS = "STANDARD_EBOOKS"


class NoteKind(StrEnum):
    INTRO = "INTRO"
    GUIDE = "GUIDE"
    MINDMAP = "MINDMAP"
    COVER = "COVER"
    OTHER = "OTHER"
