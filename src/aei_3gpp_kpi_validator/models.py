"""
Pydantic schema for a single KPI's 3GPP standards metadata and valid range.

Canonical config shape (see config/*.yml): the ``standard`` block is nested,
not flattened, so a KPI's spec/version/section metadata stays structurally
separate from its range/units/description.
"""
from typing import Optional, Union

from pydantic import BaseModel


class Standard(BaseModel):
    name: str
    version: str
    table: Optional[str] = None


class ValidRange(BaseModel):
    min: Union[int, float]
    max: Union[int, float]


class KPIStandard(BaseModel):
    standard: Standard
    description: str
    valid_range: ValidRange
    measurement_units: str
    update_frequency: str = "Release-specific"
