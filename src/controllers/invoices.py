from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from src.models.app_schemas import InvoiceProcessingResult, PresetBatchResponse
from src.service.ingest import extract_content_type, normalize_invoice_bytes
from src.service.invoice_service import InvoiceService, resolve_data_dir

_DATA_SUFFIXES = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"})


def _safe_data_filename(name: str) -> str:
    base = Path(name.strip()).name
    if not base or base != name.strip():
        raise HTTPException(status_code=400, detail="Invalid filename")
    if Path(base).suffix.lower() not in _DATA_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    return base


async def process_invoice_upload(
    service: InvoiceService,
    file: UploadFile,
) -> InvoiceProcessingResult:
    service.reset_for_new_request()
    ct = (file.content_type or "").lower()
    if ct and not (
        ct.startswith("image/") or ct in {"application/pdf", "application/octet-stream"}
    ):
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {ct}")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    return await service.process_file(
        data, filename=file.filename or "", content_type=file.content_type
    )


async def process_preset_folder(service: InvoiceService, data_dir: str) -> PresetBatchResponse:
    service.reset_for_new_request()
    path = resolve_data_dir(data_dir)
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")
    return await service.process_preset_dir(path)


def serve_atomic_preview(filename: str) -> Response:
    """Normalised PNG for the same file the graph would use."""
    safe = _safe_data_filename(filename)
    data_dir = resolve_data_dir("data")
    path = data_dir / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Not found: {safe}")
    raw = path.read_bytes()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    ct = extract_content_type(path)
    png, mime = normalize_invoice_bytes(raw, filename=safe, content_type=ct)
    return Response(content=png, media_type=mime)


def serve_data_file(filename: str) -> FileResponse:
    """Serve ``data/<filename>`` inline (PDF / image preview in the UI)."""
    safe = _safe_data_filename(filename)
    data_dir = resolve_data_dir("data")
    path = data_dir / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Not found: {safe}")
    ct = extract_content_type(path)
    return FileResponse(
        path,
        media_type=ct,
        filename=safe,
        content_disposition_type="inline",
    )


def list_data_invoice_files() -> dict[str, str | list[str]]:
    """Sorted list of invoice files in ./data."""
    data = resolve_data_dir("data")
    if not data.is_dir():
        return {"data_dir": str(data.resolve()), "files": []}
    files = sorted(
        f.name for f in data.iterdir() if f.is_file() and f.suffix.lower() in _DATA_SUFFIXES
    )
    return {"data_dir": str(data.resolve()), "files": files}


async def process_invoice_from_data(
    service: InvoiceService,
    filename: str,
) -> InvoiceProcessingResult:
    """Load from ./data and run the pipeline."""
    safe = _safe_data_filename(filename)
    data_dir = resolve_data_dir("data")
    path = data_dir / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Not found: {safe}")
    service.reset_for_new_request()
    raw = path.read_bytes()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    ct = extract_content_type(path)
    return await service.process_file(raw, filename=safe, content_type=ct)
