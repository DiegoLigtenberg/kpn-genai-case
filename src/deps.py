from fastapi import Request

from src.service.invoice_service import InvoiceService


def get_invoice_service(request: Request) -> InvoiceService:
    """InvoiceService from app.state (created at startup)."""
    return request.app.state.invoice_service
