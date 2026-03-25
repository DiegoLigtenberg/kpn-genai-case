from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, Response

from src.deps import get_invoice_service
from src.models.app_schemas import InvoiceProcessingResult, LlmTypeBody, PresetBatchResponse
from src.service.ingest import extract_content_type, normalize_invoice_bytes
from src.service.invoice_service import InvoiceService, resolve_data_dir

router = APIRouter(tags=["invoices"])

_INVOICE_SUFFIXES = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"})


def _data_file(filename: str) -> Path:
    return resolve_data_dir("data") / Path(filename).name


@router.get("/invoices/data-files")
def get_data_invoice_files() -> dict[str, str | list[str]]:
    data = resolve_data_dir("data")
    files = sorted(
        f.name for f in data.iterdir() if f.is_file() and f.suffix.lower() in _INVOICE_SUFFIXES
    )
    return {"data_dir": str(data.resolve()), "files": files}


@router.get("/invoices/raw-data-file")
def get_raw_data_file(filename: str = Query(...)) -> FileResponse:
    path = _data_file(filename)
    ct = extract_content_type(path)
    return FileResponse(
        path,
        media_type=ct,
        filename=path.name,
        content_disposition_type="inline",
    )


@router.get("/invoices/atomic-preview")
def get_atomic_preview(filename: str = Query(...)) -> Response:
    path = _data_file(filename)
    raw = path.read_bytes()
    ct = extract_content_type(path)
    png, mime = normalize_invoice_bytes(raw, filename=path.name, content_type=ct)
    return Response(content=png, media_type=mime)


@router.get("/invoices/llm")
def get_llm_setting(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> dict[str, str]:
    return {"llm_type": service.get_llm_type()}


@router.put("/invoices/llm")
def put_llm_setting(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    body: LlmTypeBody,
) -> dict[str, str]:
    return {"llm_type": service.set_llm_type(body.llm_type)}


@router.post("/invoices/process-data-file", response_model=InvoiceProcessingResult)
async def process_invoice_from_data(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    filename: str = Query(...),
) -> InvoiceProcessingResult:
    service.reset_for_new_request()
    path = _data_file(filename)
    return await service.process_file(
        path.read_bytes(),
        filename=path.name,
        content_type=extract_content_type(path),
    )


@router.post("/invoices/process", response_model=InvoiceProcessingResult)
async def process_invoice(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    file: UploadFile = File(...),
) -> InvoiceProcessingResult:
    service.reset_for_new_request()
    data = await file.read()
    return await service.process_file(
        data, filename=file.filename or "", content_type=file.content_type
    )


@router.post("/invoices/process-preset", response_model=PresetBatchResponse)
async def process_preset_data(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    data_dir: str = Query("data"),
) -> PresetBatchResponse:
    service.reset_for_new_request()
    return await service.process_preset_dir(resolve_data_dir(data_dir))
