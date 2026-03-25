from enum import Enum
from typing import Dict, Optional, Union

from pydantic import BaseModel, Field


class RuleId(str, Enum):
    """Enums for failed extraction reasons."""

    RULE_MAX_TOTAL = "RULE_MAX_TOTAL"
    RULE_MIN_YEAR = "RULE_MIN_YEAR"
    RULE_REQUIRED_FIELDS = "RULE_REQUIRED_FIELDS"
    RULE_GROSS_SUM_MISMATCH = "RULE_GROSS_SUM_MISMATCH"
    RULE_LINE_CAP = "RULE_LINE_CAP"
    RULE_DUPLICATE = "RULE_DUPLICATE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"


class PolicyDecision(str, Enum):
    """Decision after the policies have been evaluated."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class PolicyViolation(BaseModel):
    rule_id: str
    message: str


class PolicyResult(BaseModel):
    decision: PolicyDecision
    violations: list[PolicyViolation] = Field(default_factory=list)


class PolicySettings(BaseModel):
    limits: Dict[str, Union[float, int]]


class PolicySettingsPatch(BaseModel):
    limits: Optional[Dict[str, Union[float, int]]] = None
