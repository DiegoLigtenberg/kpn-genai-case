from typing import Annotated

from fastapi import APIRouter, Depends

from src.deps import get_invoice_service
from src.models.policy_schemas import PolicySettings, PolicySettingsPatch
from src.service.invoice_service import InvoiceService

router = APIRouter(tags=["policy"])


@router.get("/policy", response_model=PolicySettings)
def get_policy(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> PolicySettings:
    """Active limits in memory."""
    return service.get_policy_settings()


@router.get("/policy/defaults", response_model=PolicySettings)
def get_policy_defaults(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> PolicySettings:
    """Values read from ``policy.yaml`` on disk (does not change live policy)."""
    return service.get_policy_defaults_from_file()


@router.post("/policy/reset", response_model=PolicySettings)
def reset_policy_from_file(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> PolicySettings:
    """Reset in-memory limits from policy.yaml."""
    return service.reset_policy_from_file()


@router.put("/policy", response_model=PolicySettings)
def put_policy(
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    body: PolicySettingsPatch,
) -> PolicySettings:
    """Merge a patch into in-memory limits (file on disk unchanged)."""
    return service.apply_policy_patch(body)
