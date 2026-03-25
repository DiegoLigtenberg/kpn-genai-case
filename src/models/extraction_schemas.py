from typing import Optional

from pydantic import BaseModel, Field


class InvoiceExtraction(BaseModel):
    """All fields merged after the separate extractions."""

    vendor: Optional[str] = None
    buyer_name: Optional[str] = None
    invoice_date_raw: Optional[str] = None
    invoice_no: Optional[int] = None
    total_gross_worth: Optional[float] = None
    per_item_gross_worths: list[float] = Field(
        default_factory=list,
        description=(
            "Gross worth per invoiced row (same as PerItemGrossExtract); "
            "sum should match total_gross_worth when both are present."
        ),
    )
    image_path: Optional[str] = None
    already_exists: bool = False


class VendorExtract(BaseModel):
    """Vendor name from the invoice image."""

    vendor: Optional[str] = Field(default=None, description="Seller / supplier name only")


class BuyerExtract(BaseModel):
    """Buyer name from the invoice image."""

    buyer_name: Optional[str] = Field(default=None, description="Client / buyer name only")


class InvoiceDateExtract(BaseModel):
    """Invoice date string from the invoice image."""

    invoice_date_raw: Optional[str] = Field(
        default=None,
        description="Date of issue as printed (verbatim string)",
    )


class InvoiceNoExtract(BaseModel):
    """Invoice number from the invoice image."""

    invoice_no: Optional[int] = Field(default=None, description="Invoice number as integer")


class TotalGrossExtract(BaseModel):
    """Total gross amount from the invoice image."""

    total_gross_worth: Optional[float] = Field(
        default=None,
        description="Final total gross / amount due (numeric)",
    )


class PerItemGrossExtract(BaseModel):
    """Per-line gross amounts (top to bottom) from the invoice image."""

    per_item_gross_worths: list[float] = Field(
        default_factory=list,
        description=(
            "Gross worth per invoiced item / row in the Items table, top to bottom "
            "(e.g. 'Gross worth' column); sum should match total gross."
        ),
    )
