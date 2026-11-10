"""
Pydantic schema for a single KPI's 3GPP standards metadata and valid range.

Canonical config shape (see config/*.yml): the ``standard`` block is nested,
not flattened, so a KPI's spec/version/section metadata stays structurally
separate from its range/units/description.
"""
import math
from typing import Optional, Union

from pydantic import BaseModel, model_validator


class Standard(BaseModel):
    name: str
    version: str
    table: Optional[str] = None


class ValidRange(BaseModel):
    min: Union[int, float]
    max: Union[int, float]

    @model_validator(mode="after")
    def _finite_and_ordered(self) -> "ValidRange":
        # YAML accepts .nan and .inf. A NaN bound makes every comparison False, so no value would ever be counted out of range and
        # nothing would be clipped: a silent pass. Bounds must be finite and min must not exceed max.
        if not (math.isfinite(self.min) and math.isfinite(self.max)):
            raise ValueError(f"valid_range bounds must be finite numbers (got min={self.min}, max={self.max})")
        if self.min > self.max:
            raise ValueError(f"valid_range min ({self.min}) must not exceed max ({self.max})")
        return self


class KPIStandard(BaseModel):
    standard: Standard
    description: str
    valid_range: ValidRange
    measurement_units: str
    update_frequency: str = "Release-specific"
