import io
from pathlib import Path
from typing import Optional, Tuple

import fitz  # type: ignore[import-untyped]  # pymupdf, no stubs
from PIL import Image

_DEFAULT_PDF_DPI = 150
_MAX_EDGE = 2048


def pdf_first_page_to_png(data: bytes, dpi: int = _DEFAULT_PDF_DPI) -> bytes:
    """Rasterize first PDF page to PNG bytes."""
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        page = doc.load_page(0)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


def _resize_if_needed(img: Image.Image) -> Image.Image:
    w, h = img.size
    m = max(w, h)
    if m <= _MAX_EDGE:
        return img
    scale = _MAX_EDGE / m
    return img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)


def raster_to_png_bytes(data: bytes) -> Tuple[bytes, str]:
    """Decode any supported image, return PNG bytes and image/png."""
    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")
        img = _resize_if_needed(img)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "image/png"


def _is_pdf_payload(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == b"%PDF"


def normalize_invoice_bytes(
    data: bytes,
    *,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Tuple[bytes, str]:
    """Return (png_bytes, mime): PDFs become first-page PNG; rasters are decoded to PNG."""
    name = (filename or "").lower()
    ct = (content_type or "").lower()

    is_pdf = name.endswith(".pdf") or "pdf" in ct or _is_pdf_payload(data)
    if is_pdf:
        png = pdf_first_page_to_png(data)
        return png, "image/png"

    png, image_mime_type = raster_to_png_bytes(data)
    return png, image_mime_type


def extract_content_type(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".pdf":
        return "application/pdf"
    if suf in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suf == ".png":
        return "image/png"
    if suf in {".tif", ".tiff"}:
        return "image/tiff"
    return "application/octet-stream"
