from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.models.extraction_schemas import InvoiceExtraction
from src.models.policy_schemas import PolicyResult


# Graph state and response


class InvoiceProcessingResult(BaseModel):
    filename: Optional[str] = None
    extracted: Optional[InvoiceExtraction] = None
    policy: PolicyResult
    error: Optional[str] = None
    meta: dict = Field(default_factory=dict)


class InvoiceGraphState(BaseModel):
    """State of the invoice graph."""

    filename: str = ""
    content_type: str = ""
    raw_data: bytes = Field(
        default=b"", repr=False
    )  # original file bytes; do not include in str repr
    image_bytes: bytes = Field(default=b"", repr=False)  # do not include in str repr
    image_mime_type: str = "image/png"
    image_temp_path: str = ""
    extracted: Optional[InvoiceExtraction] = None
    extraction_warnings: list[str] = Field(default_factory=list)
    policy: Optional[PolicyResult] = None
    error: Optional[str] = None
    final: Optional[InvoiceProcessingResult] = None


class LlmTypeBody(BaseModel):
    llm_type: Literal["openai", "ollama"]


class BatchFileError(BaseModel):
    filename: str
    detail: str


class PresetBatchResponse(BaseModel):
    data_dir: str
    results: list[InvoiceProcessingResult]
    errors: list[BatchFileError] = Field(default_factory=list)
