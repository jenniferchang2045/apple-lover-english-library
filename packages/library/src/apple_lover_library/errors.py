from __future__ import annotations


class LibraryError(Exception):
    error_code = "LIBRARY_ERROR"


class RightsGateError(LibraryError):
    error_code = "RIGHTS_GATE_DENIED"


class NotFoundError(LibraryError):
    error_code = "NOT_FOUND"
