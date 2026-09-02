import pathlib

import pytest
import yaml
from pydantic import ValidationError

from aei_3gpp_kpi_validator.models import KPIStandard

CONFIG_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "aei_3gpp_kpi_validator" / "config"
SHIPPED_CONFIGS = sorted(CONFIG_DIR.glob("*.yml"))


def test_shipped_configs_exist():
    assert len(SHIPPED_CONFIGS) == 5, "expected exactly 5 shipped KPI configs"


@pytest.mark.parametrize("yml_path", SHIPPED_CONFIGS, ids=lambda p: p.name)
def test_shipped_config_loads(yml_path):
    """Every shipped YAML config must parse against the canonical nested schema."""
    with open(yml_path) as f:
        data = yaml.safe_load(f)
    KPIStandard(**data)


def test_kpi_standard_rejects_flat_schema():
    """The old flat schema (no nested `standard:` key) must be rejected."""
    flat_config = {
        "name": "TS 36.214",
        "version": "15.05.00",
        "table": "Section 5.1",
        "description": "Reference Signal Received Power",
        "valid_range": {"min": -140, "max": -44},
        "measurement_units": "dBm",
    }
    with pytest.raises(ValidationError):
        KPIStandard(**flat_config)


def test_kpi_standard_accepts_nested_schema():
    nested_config = {
        "standard": {"name": "TS 36.214", "version": "15.05.00", "table": "Section 5.1"},
        "description": "Reference Signal Received Power",
        "valid_range": {"min": -140, "max": -44},
        "measurement_units": "dBm",
    }
    parsed = KPIStandard(**nested_config)
    assert parsed.standard.name == "TS 36.214"
    assert parsed.valid_range.min == -140
