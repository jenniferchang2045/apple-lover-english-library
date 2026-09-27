from __future__ import annotations

from pathlib import Path


def extract_pdf_cover(pdf_path: Path, dest_png: Path, *, scale: float = 2.0) -> bool:
    """Render page 1 of a local PDF to PNG. For a file the user already imported."""
    path = Path(pdf_path)
    dest = Path(dest_png)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        return False
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return False
    try:
        document = pdfium.PdfDocument(str(path))
        if len(document) < 1:
            return False
        bitmap = document[0].render(scale=scale)
        image = bitmap.to_pil()
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, format="PNG")
        return dest.is_file() and dest.stat().st_size > 0
    except Exception:
        return False
