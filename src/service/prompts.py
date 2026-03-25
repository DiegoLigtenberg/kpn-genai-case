from typing import Type

from pydantic import BaseModel

from src.models.extraction_schemas import (
    BuyerExtract,
    InvoiceDateExtract,
    InvoiceNoExtract,
    PerItemGrossExtract,
    TotalGrossExtract,
    VendorExtract,
)

# --- vendor ---
VENDOR_SYSTEM = (
    "You look at a single invoice image. Extract only the seller / supplier (vendor) name. "
    "Ignore the client. If unclear who the vendor is, return null for vendor."
)
VENDOR_USER = "Return structured output with the field `vendor` only."

# --- buyer ---
BUYER_SYSTEM = (
    "You look at a single invoice image. Extract only the client / buyer name. "
    "Ignore the seller. If unclear what the name is, return null."
)
BUYER_USER = "Return structured output with the field `buyer_name` only."

# --- date ---
INVOICE_DATE_SYSTEM = (
    "You look at a single invoice image. Extract only the invoice date of issue, "
    "as printed (same wording/format as on the document). If missing, return null."
)
INVOICE_DATE_USER = "Return structured output with the field `invoice_date_raw` only."

# --- invoice number ---
INVOICE_NO_SYSTEM = (
    "You look at a single invoice image. Extract only the invoice number / invoice no. "
    "Return it as an integer. If missing or not numeric, return null."
)
INVOICE_NO_USER = "Return structured output with the field `invoice_no` only."

# --- total gross ---
TOTAL_GROSS_SYSTEM = (
    "You look at a single invoice image. Extract only the final total gross amount due "
    "(summary total gross, not per line). Return a number only. If missing, return null."
)
TOTAL_GROSS_USER = "Return structured output with the field `total_gross_worth` only."

# --- per-item gross (sums to total gross) ---
PER_ITEM_GROSS_SYSTEM = (
    "You look at a single invoice image. In the Items / line items table, extract the "
    "gross worth for each row (per item, including VAT, e.g. 'Gross worth' column), "
    "in order from top to bottom. One float per row. If there is no such table, return an empty list."
)
PER_ITEM_GROSS_USER = "Return structured output with the field `per_item_gross_worths` only."


def extract_tasks() -> list[tuple[Type[BaseModel], str, str]]:
    """Same order as graph_nodes._merge_extractions unpacks."""
    return [
        (VendorExtract, VENDOR_SYSTEM, VENDOR_USER),
        (BuyerExtract, BUYER_SYSTEM, BUYER_USER),
        (InvoiceDateExtract, INVOICE_DATE_SYSTEM, INVOICE_DATE_USER),
        (InvoiceNoExtract, INVOICE_NO_SYSTEM, INVOICE_NO_USER),
        (TotalGrossExtract, TOTAL_GROSS_SYSTEM, TOTAL_GROSS_USER),
        (PerItemGrossExtract, PER_ITEM_GROSS_SYSTEM, PER_ITEM_GROSS_USER),
    ]
