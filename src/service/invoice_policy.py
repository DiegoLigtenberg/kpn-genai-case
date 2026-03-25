import hashlib
import threading
from datetime import date
from pathlib import Path
from typing import Optional

import yaml
from dateutil import parser as date_parser

from src.models.extraction_schemas import InvoiceExtraction
from src.models.policy_schemas import (
    PolicyDecision,
    PolicyResult,
    PolicySettings,
    PolicyViolation,
    RuleId,
)
from src.service.temp_storage import append_fingerprint

_DEFAULT_POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "policy.yaml"


def evaluate_policy(
    ext: InvoiceExtraction,
    *,
    settings: PolicySettings,
) -> PolicyResult:
    """Evaluate the policy for the given invoice extraction compared to policy settings business logic."""
    
    # list of violations that will be returned by the policy node
    violations: list[PolicyViolation] = []
    # limits from the policy settings
    lim = dict(settings.limits)
    max_total = float(lim["max_total_eur"])
    min_year = int(lim["min_invoice_year"])
    tol = float(lim["line_total_sum_tolerance_eur"])
    max_line = float(lim["max_line_item_amount_eur"])

    total = ext.total_gross_worth
    inv_date = parse_invoice_date(ext.invoice_date_raw)

    # Required fields — one violation each so the UI can list every issue
    if not (ext.vendor or "").strip():
        violations.append(
            PolicyViolation(
                rule_id=RuleId.RULE_REQUIRED_FIELDS.value,
                message="Missing required field: vendor",
            )
        )
    if inv_date is None:
        violations.append(
            PolicyViolation(
                rule_id=RuleId.RULE_REQUIRED_FIELDS.value,
                message="Missing required field: invoice_date",
            )
        )
    if not (ext.buyer_name or "").strip():
        violations.append(
            PolicyViolation(
                rule_id=RuleId.RULE_REQUIRED_FIELDS.value,
                message="Missing required field: buyer_name",
            )
        )
    if total is None:
        violations.append(
            PolicyViolation(
                rule_id=RuleId.RULE_REQUIRED_FIELDS.value,
                message="Missing required field: total_amount",
            )
        )

    if ext.already_exists:
        violations.append(
            PolicyViolation(
                rule_id=RuleId.RULE_DUPLICATE.value,
                message="Duplicate invoice (already submitted)",
            )
        )

    if total is not None and total > max_total:
        violations.append(
            PolicyViolation(
                rule_id=RuleId.RULE_MAX_TOTAL.value,
                message=f"total {total} exceeds {max_total}",
            )
        )

    if inv_date is not None and inv_date.year < min_year:
        violations.append(
            PolicyViolation(
                rule_id=RuleId.RULE_MIN_YEAR.value,
                message=f"year {inv_date.year} before {min_year}",
            )
        )

    # per_item_gross_worths: sum vs document total, violation if the sum is not within the tolerance
    lines = ext.per_item_gross_worths
    if total is not None and lines:
        s = sum(lines)
        if abs(s - total) > tol:
            violations.append(
                PolicyViolation(
                    rule_id=RuleId.RULE_GROSS_SUM_MISMATCH.value,
                    message=(
                        f"sum(per-item gross)={s:.2f} vs document total={total:.2f} (tol {tol})"
                    ),
                )
            )

    for i, amt in enumerate(lines, start=1):
        if amt > max_line:
            violations.append(
                PolicyViolation(
                    rule_id=RuleId.RULE_LINE_CAP.value,
                    message=f"Per-item row {i}: gross worth {amt} exceeds {max_line}",
                )
            )

    decision = PolicyDecision.REJECT if violations else PolicyDecision.ACCEPT
    return PolicyResult(decision=decision, violations=violations)


def parse_invoice_date(raw: Optional[str]) -> Optional[date]:
    if not raw or not str(raw).strip():
        return None
    try:
        return date_parser.parse(str(raw), dayfirst=False, yearfirst=False).date()
    except (ValueError, TypeError, OverflowError):
        return None


def load_policy_settings(path: Optional[Path] = None) -> PolicySettings:
    p = path or _DEFAULT_POLICY_PATH
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return PolicySettings.model_validate(raw)


class PolicySettingsHolder:
    """Holds PolicySettings in memory; graph reads via get()."""

    def __init__(self, settings: PolicySettings) -> None:
        self._settings = settings

    def get(self) -> PolicySettings:
        return self._settings

    def set(self, settings: PolicySettings) -> None:
        self._settings = settings


def fingerprint(ext: InvoiceExtraction) -> Optional[str]:
    inv_date = parse_invoice_date(ext.invoice_date_raw)
    if (
        ext.vendor is None
        or ext.invoice_no is None
        or inv_date is None
        or ext.total_gross_worth is None
    ):
        return None
    key = "|".join(
        [
            ext.vendor.strip().lower(),
            str(ext.invoice_no),
            inv_date.isoformat(),
            f"{float(ext.total_gross_worth):.4f}",
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class DuplicateRegistry:
    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._seen.clear()

    def register_if_new(self, fp: str) -> bool:
        with self._lock:
            if fp in self._seen:
                return False
            self._seen.add(fp)
        append_fingerprint(fp)
        return True


def apply_duplicate_flag(
    ext: InvoiceExtraction, duplicates: DuplicateRegistry
) -> InvoiceExtraction:
    """Set already_exists if this fingerprint was seen earlier."""
    fp = fingerprint(ext)
    if not fp:
        return ext.model_copy(update={"already_exists": False})
    is_new = duplicates.register_if_new(fp)
    return ext.model_copy(update={"already_exists": not is_new})
