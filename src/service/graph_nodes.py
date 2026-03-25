import asyncio
import base64
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Optional, cast

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.models.app_schemas import InvoiceGraphState, InvoiceProcessingResult
from src.models.extraction_schemas import (
    BuyerExtract,
    InvoiceDateExtract,
    InvoiceExtraction,
    InvoiceNoExtract,
    PerItemGrossExtract,
    TotalGrossExtract,
    VendorExtract,
)
from src.models.policy_schemas import (
    PolicyDecision,
    PolicyResult,
    PolicyViolation,
    RuleId,
)
from src.service.ingest import normalize_invoice_bytes
from src.service.temp_storage import write_temp_png
from src.service.invoice_policy import (
    DuplicateRegistry,
    PolicySettingsHolder,
    apply_duplicate_flag,
    evaluate_policy,
)
from src.service.prompts import extract_tasks


def atomic_image_node(state: InvoiceGraphState) -> InvoiceGraphState:
    """Turn the upload into a PNG on disk for downstream vision steps.

    Args:
        state: Graph state.
        - state.raw_data:      Original upload bytes; PDF, Tiff, Jpeg, Png, etc.

    Adjusts:
        - state.image_bytes:      Normalized rawe_data to PNG bytes.
        - state.image_mime_type:  MIME type of that PNG used in this pipeline (image/png).
        - state.image_temp_path:  Path to the temp PNG file.
        - state.error:            Whether this node failed or not.

    Returns:
        The state instance with updated fields.
    """
    if state.error:
        return state
    try:
        # if the raw_data contains PDF
        if state.raw_data:
            png, mime = normalize_invoice_bytes(
                state.raw_data,
                filename=state.filename,
                content_type=state.content_type,
            )
            temp_path = write_temp_png(png)
            state.image_bytes = png
            state.image_mime_type = mime
            state.image_temp_path = temp_path
            return state

        # if the raw_data contains an image
        if state.image_bytes:
            state.image_temp_path = write_temp_png(state.image_bytes)
            return state

        state.error = "atomic_image: missing raw_data or image_bytes"
        return state
    except Exception as exc:  # noqa: BLE001
        state.error = f"atomic_image_failed: {exc}\n{traceback.format_exc()}"
        return state


def make_extract_node(
    llm: Any,
    duplicates: DuplicateRegistry,
) -> Callable[[InvoiceGraphState], Awaitable[InvoiceGraphState]]:
    async def extract_node(state: InvoiceGraphState) -> InvoiceGraphState:
        """Extract business entities from the atomic image PNG and merge into a single InvoiceExtraction.

        This function runs parallel vision calls to extract the fields.

        Args:
            state: Graph state.
            - state.image_bytes:     The encoded to base64 of the noramlized atomic image PNG.

        Adjusts:
            - state.extracted:              Filled on success; cleared on failure for the business entities
            - state.image_temp_path:        The path to the temp PNG file. Stored on the merged extraction as image_path.
            - state.extraction_warnings:    Only when some vision calls failed but not all.
            - state.error:                  Whether this node failed or not.

        Returns:
            The state instance with updated fields.
        """
        if state.error:
            return state
        if not state.image_bytes:
            state.error = "extraction_failed: no normalized image after atomic_image"
            state.extracted = None
            return state
        try:
            b64 = base64.b64encode(state.image_bytes).decode("ascii")
            mime = state.image_mime_type

            # the task list is a list of tuples,
            # each tuple contains a model class, a system prompt, and a user prompt
            # together they form the prompt for the vision call to gather a specific business entity
            # the tasks are ran asynchronously to increase the speed of the extraction process
            subtasks = extract_tasks()
            results = await asyncio.gather(
                *[
                    _run_structured_async(llm, model_cls, system_prompt, user_prompt, b64, mime)
                    for model_cls, system_prompt, user_prompt in subtasks
                ],
                return_exceptions=True,
            )

            # handles failed tasks and adds them to the warnings list
            models: list[BaseModel] = []
            warnings: list[str] = []
            for (model_cls, _system, _user), result in zip(subtasks, results, strict=True):
                if isinstance(result, BaseException):
                    models.append(model_cls())
                    warnings.append(f"{model_cls.__name__}: {result}")
                else:
                    models.append(result)

            if len(warnings) == len(subtasks):
                state.error = "extraction_failed: all vision subtasks failed.\n" + "\n".join(
                    warnings
                )
                state.extracted = None
                return state

            # casts the results to the expected model classes
            (
                vendor_extract,
                buyer_extract,
                invoice_date_extract,
                invoice_no_extract,
                total_gross_extract,
                per_item_gross_extract,
            ) = cast(
                tuple[
                    VendorExtract,
                    BuyerExtract,
                    InvoiceDateExtract,
                    InvoiceNoExtract,
                    TotalGrossExtract,
                    PerItemGrossExtract,
                ],
                tuple(models),
            )
            ext = _merge_extractions(
                vendor_extract,
                buyer_extract,
                invoice_date_extract,
                invoice_no_extract,
                total_gross_extract,
                per_item_gross_extract,
                state.image_temp_path,
            )
            ext = apply_duplicate_flag(ext, duplicates)
            state.extracted = ext
            if warnings:
                state.extraction_warnings = warnings
            return state
        except Exception as exc:  # noqa: BLE001
            state.error = f"extraction_failed: {exc}\n{traceback.format_exc()}"
            state.extracted = None
            return state

    return extract_node


def make_policy_node(
    holder: PolicySettingsHolder,
) -> Callable[[InvoiceGraphState], InvoiceGraphState]:
    def policy_node(state: InvoiceGraphState) -> InvoiceGraphState:
        """Evaluate policy rules and fold in extraction warnings.

        Args:
            state: Graph state.
            - state.extracted:           If missing, policy rejects without rule math.
            - state.extraction_warnings: Added as policy violations when present.
            - state.error:               Whether this node failed or not.

        Adjusts:
            - state.policy: Accept or reject with the combined violations.

        Returns:
            The state instance with updated fields.
        """
        if state.error:
            state.policy = PolicyResult(
                decision=PolicyDecision.REJECT,
                violations=[
                    PolicyViolation(
                        rule_id=RuleId.EXTRACTION_FAILED.value,
                        message=state.error or "extraction failed",
                    )
                ],
            )
            return state
        if state.extracted is None:
            state.policy = PolicyResult(
                decision=PolicyDecision.REJECT,
                violations=[
                    PolicyViolation(
                        rule_id=RuleId.EXTRACTION_FAILED.value,
                        message="no extraction",
                    )
                ],
            )
            return state
        pr = evaluate_policy(state.extracted, settings=holder.get())
        violations = list(pr.violations)
        for w in state.extraction_warnings:
            violations.append(
                PolicyViolation(
                    rule_id=RuleId.EXTRACTION_FAILED.value,
                    message=w,
                )
            )
        decision = PolicyDecision.REJECT if violations else PolicyDecision.ACCEPT
        state.policy = PolicyResult(decision=decision, violations=violations)
        return state

    return policy_node


def final_decision_node(state: InvoiceGraphState) -> InvoiceGraphState:
    """Build the API-facing InvoiceProcessingResult from the graph state.

    Args:
        state: Graph state.
        - state.filename:   Copied into the result.
        - state.extracted: Copied into the result.
        - state.policy:    Copied into the result.
        - state.error:     Copied into the result.
        - state.image_mime_type, state.extracted.image_path: Used when building meta.

    Adjusts:
        - state.final: InvoiceProcessingResult for the API response.

    Returns:
        The state instance with updated fields.
    """
    state.final = InvoiceProcessingResult(
        filename=state.filename or None,
        extracted=state.extracted,
        policy=state.policy or PolicyResult(decision=PolicyDecision.REJECT, violations=[]),
        error=state.error,
        meta=_response_meta(state),
    )
    return state


# helpers


def _vision_block(system: str, user: str, b64: str, mime: str) -> list:
    return [
        SystemMessage(content=system),
        HumanMessage(
            content=[
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]
        ),
    ]


async def _run_structured_async(
    llm: Any,
    model_cls: type[BaseModel],
    system: str,
    user: str,
    b64: str,
    mime: str,
) -> BaseModel:
    chain = llm.with_structured_output(model_cls)
    return await chain.ainvoke(_vision_block(system, user, b64, mime))


def _norm_str(value: Optional[str]) -> Optional[str]:
    """Normalise a string value by removing whitespace."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _merge_extractions(
    vendor_extract: VendorExtract,
    buyer_extract: BuyerExtract,
    invoice_date_extract: InvoiceDateExtract,
    invoice_no_extract: InvoiceNoExtract,
    total_gross_extract: TotalGrossExtract,
    per_item_gross_extract: PerItemGrossExtract,
    image_path: str,
) -> InvoiceExtraction:
    return InvoiceExtraction(
        vendor=_norm_str(vendor_extract.vendor),
        buyer_name=_norm_str(buyer_extract.buyer_name),
        invoice_date_raw=_norm_str(invoice_date_extract.invoice_date_raw),
        invoice_no=invoice_no_extract.invoice_no,
        total_gross_worth=total_gross_extract.total_gross_worth,
        per_item_gross_worths=list(per_item_gross_extract.per_item_gross_worths),
        image_path=image_path or None,
    )


def _response_meta(s: InvoiceGraphState) -> dict[str, Any]:
    meta: dict[str, Any] = {"image_mime_type": s.image_mime_type}
    ext = s.extracted
    if ext is not None and ext.image_path:
        meta["image_bytes_on_disk"] = Path(ext.image_path).stat().st_size
    return meta
